#!/bin/bash

set -e
. $(dirname "${0}")/../.env
RUN_FILE=${PSW_WORKSPACE}/scripts/run2.sh
ENV_FILE=".env"
if [ ! -f "$RUN_FILE" ]; then
    echo "Error: $RUN_FILE not found in current directory."
    exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found in current directory."
    exit 1
fi


extend_run_sh() {
    local core="$1"

    # 检查是否已存在
    if grep -q -- "--core $core" "$RUN_FILE"; then
        echo "[run.sh] Skip: $core already exists"
        return
    fi

    # 准备插入的 elif 内容
    local block=""
    block+="    elif [ \"\$arg\" = \"$core\" ] && [ \${CORE_SPECIFIED} == 0 ]; then\n"
    block+="        CMD_OPTIONS=\"\${CMD_OPTIONS} --core $core\"\n"
    block+="        CORE_SPECIFIED=1\n"

    # 插入到 AUTO-GENERATED-START / AUTO-GENERATED-END 中间
    awk -v CORE_BLOCK="$block" '
        /# AUTO-GENERATED-START/ {
            print
            print CORE_BLOCK
            inblock=1
            next
        }
        /# AUTO-GENERATED-END/ {
            inblock=0
            print
            next
        }
        inblock { next }
        { print }
    ' "$RUN_FILE" > "${RUN_FILE}.tmp"

    mv "${RUN_FILE}.tmp" "$RUN_FILE"
    chmod +x "$RUN_FILE"
    echo "[run.sh] Added: $core"
}

###########################################################################
# PART 2: 扩展 .env
###########################################################################

extend_env() {
    local core="$1"
    local CORE_UPPER=$(echo "$core" | tr '[:lower:]' '[:upper:]')

    # 最终希望插入的行
    local newline="export PSW_TARGETSW_${CORE_UPPER}_EMBENCH=\${PSW_TARGETSW_EXAMPLES}/${core}/embench"

    # 如果已经存在，则跳过
    if grep -q "$newline" "$ENV_FILE"; then
        echo "[.env] Skip: $core already exists"
        return
    fi

    # 使用 awk 插入到 AUTO-GENERATED-START / AUTO-GENERATED-END 之间
    awk -v NEWLINE="$newline" '
        /# AUTO-GENERATED-START/ {
            print;
            print NEWLINE;   # 插入新内容
            inblock=1;
            next;
        }

        /# AUTO-GENERATED-END/ {
            inblock=0;
            print;
            next;
        }

        inblock { next }  # 删除旧生成内容

        { print }
    ' "$ENV_FILE" > "${ENV_FILE}.tmp"

    mv "${ENV_FILE}.tmp" "$ENV_FILE"
    echo "[.env] Added: $newline"
}



copy_template_embench() {
    local core="$1"

    # 获取根目录（必须 source .env）
    if [ -z "$PSW_TARGETSW_EXAMPLES" ]; then
        echo "[copy] ERROR: Please 'source .env' before running extend_run.sh"
        exit 1
    fi

    local template="${PSW_TARGETSW_EXAMPLES}/cv32e40p/embench"
    local target="${PSW_TARGETSW_EXAMPLES}/${core}/embench"

    # 如果目录已存在，跳过
    if [ -d "$target" ]; then
        echo "[copy] Skip: $target already exists"
        return
    fi

    # 创建父目录
    mkdir -p "${PSW_TARGETSW_EXAMPLES}/${core}"

    # 复制模板
    cp -r "$template" "$target"

    echo "[copy] Created template for core '$core':"
    echo "       $target"
}


generate_ini_file() {
    local core="$1"
    local isa="$2"

    if [ -z "$PSW_PERF_SIM" ]; then
        echo "[ini] ERROR: PSW_PERF_SIM is not set. Please 'source .env'."
        exit 1
    fi

    local ini_dir="${PSW_PERF_SIM}/simulator/ini"
    local ini_file="${ini_dir}/${core}.ini"

    # mkdir -p "$ini_dir"

    if [ -f "$ini_file" ]; then
        echo "[ini] Skip: $ini_file already exists"
        return
    fi

    cat > "$ini_file" <<EOF
[StringConfigurations]
 jit.type=TCCJIT
 arch.cpu=${isa}

[IntConfigurations]
 simple_mem_system.memseg_origin_00=0x00000000
 simple_mem_system.memseg_length_00=0x00080000
 simple_mem_system.memseg_origin_01=0x00080000
 simple_mem_system.memseg_length_01=0x00080000

[Plugin Logger]
 plugin.logger.logaddr=0x10000000
 plugin.logger.logmask=0xF0000000
EOF

    echo "[ini] Created: $ini_file"
}

###########################################################################
# MAIN 
###########################################################################

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <core_name> <ISA>"
    echo "Example: $0 rv1 RV64IMACFD"
    exit 1
fi

core_name="$1"
isa_name="$2"

echo ">>> Processing core: $core_name"
echo ">>> ISA: $isa_name"

extend_run_sh "$core_name"
extend_env "$core_name"
copy_template_embench "$core_name"
generate_ini_file "$core_name" "$isa_name"

echo "All done."

