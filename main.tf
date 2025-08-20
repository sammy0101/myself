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

resource "oci_core_instance" "ubuntu_instance" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_id
  shape               = "VM.Standard.E5.Flex"  # 示例形狀，可調整
  shape_config {
    ocpus = 1
    memory_in_gbs = 12
  }
  source_details {
    source_id   = var.image_id  # Ubuntu 或其他映像的 OCID
    source_type = "image"
  }
  create_vnic_details {
    assign_public_ip = true
    subnet_id        = var.subnet_id
  }
  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
  }
  preserve_boot_volume = false
}
