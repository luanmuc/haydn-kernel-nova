#!/usr/bin/env python3
"""Apply one haydn diagnostic config variant to arch/arm64/configs/haydn_defconfig."""
import re
import sys
from pathlib import Path

CONFIG = Path("arch/arm64/configs/haydn_defconfig")


def set_opt(text: str, name: str, enabled: bool) -> str:
    line = f"CONFIG_{name}=y" if enabled else f"# CONFIG_{name} is not set"
    pattern = re.compile(rf"^(?:# )?CONFIG_{name}(?:=.*)?$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    return text.rstrip() + "\n" + line + "\n"


VARIANTS = {
    # All three FCM5-required options stay on; only the diagnostic extras change.
    "strict-pauth": [("CFI_PERMISSIVE", False)],
    "scs-vmap-off": [("SHADOW_CALL_STACK_VMAP", False)],
    "cfi-shadow-off": [("CFI_CLANG_SHADOW", False)],
    # One required option off per branch: touch-localization, not a popup fix.
    "scs-off": [("SHADOW_CALL_STACK", False), ("SHADOW_CALL_STACK_VMAP", False)],
    "cfi-off": [
        ("CFI_CLANG", False),
        ("CFI_CLANG_SHADOW", False),
        ("CFI_PERMISSIVE", False),
    ],
    "sw-off": [("ARM64_SW_TTBR0_PAN", False)],
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in VARIANTS:
        raise SystemExit(f"usage: {sys.argv[0]} <{'|'.join(VARIANTS)}>")
    variant = sys.argv[1]
    text = CONFIG.read_text()
    for name, enabled in VARIANTS[variant]:
        text = set_opt(text, name, enabled)
    CONFIG.write_text(text)
    print(f"variant={variant}")
    for line in text.splitlines():
        if re.search(r"CONFIG_(CFI_CLANG|CFI_CLANG_SHADOW|CFI_PERMISSIVE|SHADOW_CALL_STACK|SHADOW_CALL_STACK_VMAP|ARM64_SW_TTBR0_PAN|ARM64_PTR_AUTH)=", line) or re.search(
            r"# CONFIG_(CFI_CLANG|CFI_CLANG_SHADOW|CFI_PERMISSIVE|SHADOW_CALL_STACK|SHADOW_CALL_STACK_VMAP|ARM64_SW_TTBR0_PAN|ARM64_PTR_AUTH) is not set", line
        ):
            print(line)


if __name__ == "__main__":
    main()
