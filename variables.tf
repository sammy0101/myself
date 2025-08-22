variable "tenancy_ocid" {}
variable "user_ocid" {}
variable "fingerprint" {}
variable "private_key" {}  # 改為 private_key
variable "region" {}
variable "compartment_id" {}
variable "subnet_id" {}
variable "image_id" {}
variable "ssh_public_key" {
  default = ""  # 如果不用 key，留空
}
