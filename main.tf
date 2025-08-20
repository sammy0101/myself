terraform {
  required_providers {
    oci = {
      source = "oracle/oci"
    }
    random = {
      source = "hashicorp/random"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

resource "random_password" "ssh_password" {
  length           = 16
  special          = true
  override_special = "!@#$%^&*"
}

resource "oci_core_instance" "ubuntu_instance" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_id
  shape               = "VM.Standard.A1.Flex"
  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }
  source_details {
    source_id   = var.image_id
    source_type = "image"
  }
  create_vnic_details {
    assign_public_ip = true
    subnet_id        = var.subnet_id
  }
  metadata = {
    ssh_authorized_keys = var.ssh_public_key  # 可選，如果有 SSH key
    user_data           = base64encode(<<EOF
#cloud-config
users:
  - name: ubuntu
    passwd: $${random_password.ssh_password.result}
    lock_passwd: false
ssh_pwauth: true
runcmd:
  - systemctl restart ssh
EOF
    )
  }
  preserve_boot_volume = false
}

output "instance_public_ip" {
  value = oci_core_instance.ubuntu_instance.public_ip
}

output "ssh_password" {
  value     = random_password.ssh_password.result
  sensitive = true
}
