#!/usr/bin/env python3
import psutil
import time
import subprocess
import logging
import os
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/var/log/vm_monitor.log'
)

# Configuration
THRESHOLD = 75  # Percentage threshold for auto-scaling
CHECK_INTERVAL = 60  # Check every minute
CONSECUTIVE_CHECKS = 5  # Number of consecutive high usage checks before scaling
CONFIG_FILE = '/etc/vm_monitor/config.json'

# Cloud provider selection (gcp, aws, or azure)
with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)
    CLOUD_PROVIDER = config.get('cloud_provider', 'gcp')
    INSTANCE_TYPE = config.get('instance_type', 'n1-standard-2')  # For GCP
    REGION = config.get('region', 'us-central1')

def get_system_usage():
    """Get current system resource usage percentages"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage('/').percent
    
    logging.info(f"CPU: {cpu_percent}%, Memory: {memory_percent}%, Disk: {disk_percent}%")
    
    return {
        'cpu': cpu_percent,
        'memory': memory_percent,
        'disk': disk_percent
    }

def should_migrate(usage_history):
    """Determine if migration should be triggered based on usage history"""
    if len(usage_history) < CONSECUTIVE_CHECKS:
        return False
    
    # Check last N readings for consistent high usage
    recent_checks = usage_history[-CONSECUTIVE_CHECKS:]
    high_usage_checks = 0
    
    for usage in recent_checks:
        if (usage['cpu'] > THRESHOLD or 
            usage['memory'] > THRESHOLD or 
            usage['disk'] > THRESHOLD):
            high_usage_checks += 1
    
    return high_usage_checks == CONSECUTIVE_CHECKS

def migrate_to_cloud():
    """Migrate the VM to the selected cloud provider"""
    logging.info(f"Starting migration to {CLOUD_PROVIDER}")
    
    # Create snapshot/image of the current VM
    try:
        subprocess.run([
            "sudo", "dd", "if=/dev/sda", 
            f"of=/tmp/vm_disk_image.img", "bs=4M", "status=progress"
        ], check=True)
        
        # Execute cloud-specific migration script
        if CLOUD_PROVIDER == 'gcp':
            migrate_to_gcp()
        elif CLOUD_PROVIDER == 'aws':
            migrate_to_aws()
        elif CLOUD_PROVIDER == 'azure':
            migrate_to_azure()
        else:
            logging.error(f"Unknown cloud provider: {CLOUD_PROVIDER}")
            return False
            
        return True
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        return False

def migrate_to_gcp():
    """Handle GCP-specific migration"""
    logging.info("Executing GCP migration")
    
    # Create compressed image
    subprocess.run([
        "gzip", "-c", "/tmp/vm_disk_image.img", ">", "/tmp/vm_disk_image.img.gz"
    ], shell=True, check=True)
    
    # Upload to GCS bucket
    # In the migrate_to_gcp function, change:
    subprocess.run([
                "sudo", "gsutil", "cp", "/tmp/vm_migration_package.tar.gz", 
                f"gs://{config['gcp_bucket']}/vm_migration_package.tar.gz"
                  ], check=True)
    
    # Create disk from image
    subprocess.run([
        "gcloud", "compute", "images", "create", "local-vm-image",
        "--source-uri", f"gs://{config['gcp_bucket']}/vm_disk_image.img.gz",
        "--project", config['gcp_project']
    ], check=True)
    
    # Create VM from image
    subprocess.run([
        "gcloud", "compute", "instances", "create", "migrated-vm",
        "--image", "local-vm-image",
        "--machine-type", INSTANCE_TYPE,
        "--zone", f"{REGION}-a",
        "--project", config['gcp_project']
    ], check=True)
    
    logging.info("GCP migration completed successfully")

def migrate_to_aws():
    """Handle AWS-specific migration"""
    logging.info("Executing AWS migration")
    # AWS migration code here
    # Similar steps: compress, upload to S3, import as AMI, launch EC2 instance

def migrate_to_azure():
    """Handle Azure-specific migration"""
    logging.info("Executing Azure migration")
    # Azure migration code here
    # Similar steps: compress, upload to blob storage, create managed image, deploy VM

def main():
    usage_history = []
    
    logging.info("VM monitoring service started")
    
    while True:
        usage = get_system_usage()
        usage_history.append(usage)
        
        # Keep only the most recent readings
        if len(usage_history) > CONSECUTIVE_CHECKS * 2:
            usage_history = usage_history[-CONSECUTIVE_CHECKS * 2:]
        
        # Check if we should migrate
        if should_migrate(usage_history):
            logging.warning("High resource usage detected - initiating cloud migration")
            
            if migrate_to_cloud():
                logging.info("Migration completed successfully")
                # Exit monitoring or switch to a different mode
                break
            else:
                logging.error("Migration failed, continuing monitoring")
                # Reset history after failed migration attempt
                usage_history = []
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
