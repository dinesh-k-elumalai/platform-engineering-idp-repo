#!/usr/bin/env python3
"""
Automated deployment pipeline for IDP-managed services.
Handles: build, test, security scan, deploy, and verification.

Usage:
    export SERVICE_NAME=user-api
    export DEPLOY_ENV=staging
    python pipeline.py

    Or with arguments:
    python pipeline.py --service user-api --env production --dry-run
"""
import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
import requests
from datetime import datetime


class DeploymentPipeline:
    """
    Comprehensive deployment pipeline with built-in safety checks,
    automatic rollback, and multi-stage verification.
    """
    
    def __init__(self, service_name: str, environment: str, dry_run: bool = False):
        self.service_name = service_name
        self.environment = environment
        self.dry_run = dry_run
        self.config = self._load_config()
        self.deployment_start = datetime.now()
        
    def _load_config(self) -> Dict:
        """Load service configuration from catalog"""
        catalog_path = Path("catalog-info.yaml")
        if not catalog_path.exists():
            raise FileNotFoundError("catalog-info.yaml not found")
            
        with open(catalog_path) as f:
            return yaml.safe_load(f)
    
    def _run_command(self, cmd: str, check: bool = True) -> Tuple[int, str]:
        """Execute shell command and return status"""
        if self.dry_run:
            print(f"[DRY RUN] Would execute: {cmd}")
            return 0, "dry-run-output"
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=check
            )
            return result.returncode, result.stdout
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stderr
    
    def build_image(self) -> str:
        """Build and tag container image"""
        git_sha = os.getenv("GITHUB_SHA", subprocess.getoutput("git rev-parse HEAD"))[:8]
        image_tag = f"{self.service_name}:{git_sha}"
        
        print(f"🔨 Building image: {image_tag}")
        
        # Build image
        build_cmd = f"docker build -t {image_tag} ."
        returncode, output = self._run_command(build_cmd)
        
        if returncode != 0:
            raise Exception(f"Docker build failed: {output}")
        
        # Tag and push to registry
        registry = os.getenv("REGISTRY_URL", "registry.company.com")
        full_tag = f"{registry}/{image_tag}"
        
        self._run_command(f"docker tag {image_tag} {full_tag}")
        self._run_command(f"docker push {full_tag}")
        
        print(f"✅ Image built and pushed: {full_tag}")
        return full_tag
    
    def run_tests(self) -> bool:
        """Execute comprehensive test suite"""
        print("🧪 Running test suite...")
        
        tests = [
            ("Unit tests", "pytest tests/unit -v --cov=. --cov-report=xml"),
            ("Integration tests", "pytest tests/integration -v"),
            ("Linting", "flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics"),
            ("Type checking", "mypy . --ignore-missing-imports")
        ]
        
        for test_name, test_cmd in tests:
            print(f"  Running {test_name}...")
            returncode, output = self._run_command(test_cmd, check=False)
            
            if returncode != 0:
                print(f"❌ {test_name} failed:")
                print(output)
                return False
            print(f"  ✓ {test_name} passed")
        
        print("✅ All tests passed")
        return True
    
    def security_scan(self, image_tag: str) -> bool:
        """Run container security scan with Trivy"""
        print(f"🔍 Scanning image for vulnerabilities: {image_tag}")
        
        scan_cmd = f"trivy image --severity HIGH,CRITICAL --exit-code 1 {image_tag}"
        returncode, output = self._run_command(scan_cmd, check=False)
        
        if returncode != 0:
            print("❌ Security vulnerabilities found:")
            print(output)
            
            # Check if we should proceed anyway (non-production environments)
            if self.environment in ['dev', 'staging']:
                print("⚠️  Proceeding despite vulnerabilities in non-production environment")
                return True
            return False
        
        print("✅ Security scan passed")
        return True
    
    def update_manifest(self, image_tag: str) -> None:
        """Update ArgoCD application manifest with new image"""
        manifest_path = Path(f"deploy/{self.environment}/values.yaml")
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
        print(f"📝 Updating manifest: {manifest_path}")
        
        with open(manifest_path) as f:
            values = yaml.safe_load(f)
        
        # Extract just the tag from full image path
        tag = image_tag.split(':')[1] if ':' in image_tag else 'latest'
        
        # Update image tag
        values['image']['tag'] = tag
        
        # Update metadata
        values['deployment'] = values.get('deployment', {})
        values['deployment']['lastUpdated'] = datetime.now().isoformat()
        values['deployment']['updatedBy'] = os.getenv('GITHUB_ACTOR', 'unknown')
        
        with open(manifest_path, 'w') as f:
            yaml.dump(values, f, default_flow_style=False, sort_keys=False)
        
        # Commit and push changes
        git_commands = [
            f"git add {manifest_path}",
            f"git commit -m 'Deploy {self.service_name}:{tag} to {self.environment}'",
            "git push origin main"
        ]
        
        for cmd in git_commands:
            self._run_command(cmd)
        
        print("✅ Manifest updated and pushed")
    
    def trigger_argocd_sync(self) -> bool:
        """Trigger ArgoCD application sync"""
        argocd_api = os.getenv("ARGOCD_API_URL")
        argocd_token = os.getenv("ARGOCD_TOKEN")
        
        if not argocd_api or not argocd_token:
            print("⚠️  ArgoCD credentials not configured, skipping sync trigger")
            return True
        
        app_name = f"{self.service_name}-{self.environment}"
        
        print(f"🔄 Triggering ArgoCD sync for: {app_name}")
        
        try:
            response = requests.post(
                f"{argocd_api}/api/v1/applications/{app_name}/sync",
                headers={"Authorization": f"Bearer {argocd_token}"},
                json={"prune": False, "dryRun": self.dry_run}
            )
            
            if response.status_code == 200:
                print("✅ ArgoCD sync triggered successfully")
                return True
            else:
                print(f"❌ ArgoCD sync failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to trigger ArgoCD sync: {e}")
            return False
    
    def wait_for_deployment(self, timeout: int = 600) -> bool:
        """Wait for deployment to complete and verify health"""
        print(f"⏳ Waiting for {self.service_name} deployment (timeout: {timeout}s)...")
        
        if self.dry_run:
            print("[DRY RUN] Would wait for deployment")
            return True
        
        # Use kubectl to wait for rollout
        cmd = (
            f"kubectl rollout status deployment/{self.service_name} "
            f"-n {self.environment} --timeout={timeout}s"
        )
        
        returncode, output = self._run_command(cmd, check=False)
        
        if returncode != 0:
            print(f"❌ Deployment failed or timed out:\n{output}")
            return False
        
        print("✅ Deployment completed successfully")
        
        # Verify health endpoints
        return self._verify_health()
    
    def _verify_health(self) -> bool:
        """Hit health check endpoint to verify service"""
        if self.dry_run:
            print("[DRY RUN] Would verify health")
            return True
        
        service_url = f"https://{self.service_name}.{self.environment}.company.com"
        
        print(f"🏥 Verifying service health: {service_url}/health")
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{service_url}/health", timeout=10)
                
                if response.status_code == 200:
                    print("✅ Health check passed")
                    return True
                else:
                    print(f"⚠️  Health check returned {response.status_code}, retrying...")
                    
            except Exception as e:
                print(f"⚠️  Health check failed (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(10)
        
        print("❌ Health check failed after maximum retries")
        return False
    
    def rollback(self) -> bool:
        """Rollback to previous deployment"""
        print("🔙 Initiating rollback...")
        
        cmd = f"kubectl rollout undo deployment/{self.service_name} -n {self.environment}"
        returncode, output = self._run_command(cmd, check=False)
        
        if returncode == 0:
            print("✅ Rollback completed successfully")
            return True
        else:
            print(f"❌ Rollback failed: {output}")
            return False
    
    def send_notification(self, success: bool, message: str) -> None:
        """Send deployment notification to Slack"""
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        
        if not webhook_url:
            return
        
        duration = (datetime.now() - self.deployment_start).total_seconds()
        
        color = "good" if success else "danger"
        emoji = "✅" if success else "❌"
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"{emoji} Deployment {'Succeeded' if success else 'Failed'}",
                "fields": [
                    {"title": "Service", "value": self.service_name, "short": True},
                    {"title": "Environment", "value": self.environment, "short": True},
                    {"title": "Duration", "value": f"{duration:.0f}s", "short": True},
                    {"title": "Status", "value": message, "short": False}
                ]
            }]
        }
        
        try:
            requests.post(webhook_url, json=payload)
        except Exception as e:
            print(f"⚠️  Failed to send notification: {e}")
    
    def deploy(self) -> bool:
        """Execute full deployment pipeline"""
        print(f"\n{'='*60}")
        print(f"🚀 Starting deployment for {self.service_name} to {self.environment}")
        print(f"{'='*60}\n")
        
        try:
            # Phase 1: Testing
            if not self.run_tests():
                self.send_notification(False, "Tests failed")
                return False
            
            # Phase 2: Build
            image_tag = self.build_image()
            
            # Phase 3: Security
            if not self.security_scan(image_tag):
                self.send_notification(False, "Security scan failed")
                return False
            
            # Phase 4: Deploy
            self.update_manifest(image_tag)
            
            if not self.trigger_argocd_sync():
                self.send_notification(False, "Failed to trigger ArgoCD sync")
                return False
            
            # Phase 5: Verify
            if not self.wait_for_deployment():
                print("⚠️  Deployment verification failed, initiating rollback...")
                self.rollback()
                self.send_notification(False, "Deployment failed, rolled back")
                return False
            
            # Success!
            duration = (datetime.now() - self.deployment_start).total_seconds()
            print(f"\n{'='*60}")
            print(f"✅ Successfully deployed {image_tag} to {self.environment}")
            print(f"⏱️  Total deployment time: {duration:.0f} seconds")
            print(f"{'='*60}\n")
            
            self.send_notification(True, f"Deployed {image_tag} in {duration:.0f}s")
            return True
            
        except Exception as e:
            print(f"\n❌ Deployment failed with error: {e}")
            self.send_notification(False, f"Deployment error: {str(e)}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy services through the Internal Developer Platform"
    )
    parser.add_argument(
        "--service",
        default=os.getenv("SERVICE_NAME"),
        help="Service name to deploy"
    )
    parser.add_argument(
        "--env",
        default=os.getenv("DEPLOY_ENV", "staging"),
        choices=["dev", "staging", "production"],
        help="Target environment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute in dry-run mode (no actual changes)"
    )
    
    args = parser.parse_args()
    
    if not args.service:
        print("❌ Error: SERVICE_NAME must be provided via --service or environment variable")
        sys.exit(1)
    
    pipeline = DeploymentPipeline(args.service, args.env, args.dry_run)
    success = pipeline.deploy()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
