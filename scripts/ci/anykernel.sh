### AnyKernel3 Ramdisk Mod Script
## osm0sis @ xda-developers
## 本项目（HoshinoNeko / SM8350）专用模板
## 关键前提：SM8350 是 boot image v3（独立 vendor_boot，无 init_boot）
##          所以 block=boot；dtb/dtbo 不打包，沿用 ROM 原机 dtbo

### AnyKernel setup
properties() { '
kernel.string=HoshinoNeko Kernel · haydn (K40 Pro/Pro+)
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=0
device.name1=haydn
device.name2=haydnpro
device.name3=M2012K11C
device.name4=
device.name5=
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
'; }

### AnyKernel install
block=boot
is_slot_device=0
ramdisk_compression=auto
patch_vbmeta_flag=auto
no_magisk_check=1

# 引入 AK3 核心函数（不要删除）
. tools/ak3-core.sh
AKHOME="${AKHOME:-$(pwd)}"

if [ ! -f "$AKHOME/Image" ]; then
    abort "  -> No kernel Image found in this zip! Aborting."
fi

# boot 分区安装
dump_boot
write_boot
## end boot install
