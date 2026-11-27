### AnyKernel3 Ramdisk Mod Script
## osm0sis @ xda-developers
## 本项目（HoshinoNeko / SM8350）专用模板
## 关键前提：SM8350 是 boot image v3（独立 vendor_boot，无 init_boot）
##          所以目标块是 boot；dtb/dtbo 不打包，沿用 ROM 原机 dtbo
##          TWRP 环境可能缺少 by-name/boot_a；下面显式解析并写入大写 BLOCK

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
# haydn/TWRP sometimes lacks the /dev/block/by-name/boot_a symlink.
# Resolve the active boot block explicitly instead of relying on AK3's auto search.
slot=$(getprop ro.boot.slot_suffix 2>/dev/null)
if [ -z "$slot" ]; then
  slot=$(grep -o 'androidboot.slot_suffix=[^ ]*' /proc/cmdline 2>/dev/null | cut -d= -f2)
fi
if [ -z "$slot" ]; then
  slot=$(getprop ro.boot.slot 2>/dev/null)
  [ -n "$slot" ] && slot="_$slot"
fi
[ "$slot" = "_normal" ] && slot=""
block=
for p in \
  /dev/block/by-name/boot$slot \
  /dev/block/bootdevice/by-name/boot$slot \
  /dev/block/platform/*/by-name/boot$slot \
  /dev/block/platform/*/*/by-name/boot$slot \
  /dev/block/by-name/boot \
  /dev/block/bootdevice/by-name/boot \
  /dev/block/platform/*/by-name/boot \
  /dev/block/platform/*/*/by-name/boot; do
  if [ -e "$p" ]; then
    block=$p
    break
  fi
done
[ -z "$block" ] && block=__no_boot_partition__
# ak3-core.sh 读取的是大写变量；原包写成小写，导致 BLOCK 为空。
BLOCK=$block
IS_SLOT_DEVICE=0
RAMDISK_COMPRESSION=auto
PATCHVBMETAFLAG=auto
NO_MAGISK_CHECK=1

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
