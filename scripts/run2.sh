#!/bin/bash

set -e

. $(dirname "${0}")/../.env

TARGET_SW=$1
shift

CMD_OPTIONS=""
CORE_SPECIFIED=0

while [ "$#" -gt 0 ];
do
    arg="$1"
    if [ "$arg" = "cv32e40p" ] && [ ${CORE_SPECIFIED} == 0 ]; then
	CMD_OPTIONS="${CMD_OPTIONS} --core cv32e40p"
	CORE_SPECIFIED=1
    elif [ "$arg" = "cva6" ] && [ ${CORE_SPECIFIED} == 0 ]; then
	CMD_OPTIONS="${CMD_OPTIONS} --core cva6"
	CORE_SPECIFIED=1
    elif [ "$arg" = "CVA6_QWEN_1" ] && [ ${CORE_SPECIFIED} == 0 ]; then
        CMD_OPTIONS="${CMD_OPTIONS} --core CVA6_QWEN_1"
        CORE_SPECIFIED=1
    elif [ "$arg" = "ROCKET" ] && [ ${CORE_SPECIFIED} == 0 ]; then
        CMD_OPTIONS="${CMD_OPTIONS} --core ROCKET"
        CORE_SPECIFIED=1
    # AUTO-GENERATED-START
    elif [ "$arg" = "RC" ] && [ ${CORE_SPECIFIED} == 0 ]; then
        CMD_OPTIONS="${CMD_OPTIONS} --core RC"
        CORE_SPECIFIED=1

    # AUTO-GENERATED-END
    else
	CMD_OPTIONS="${CMD_OPTIONS} ${arg}"
    fi
    shift
done

if [ ${CORE_SPECIFIED} == 1 ]; then
    ${PSW_SCRIPTS_SUPPORT}/run_helper.py ${TARGET_SW} ${CMD_OPTIONS}
else
    echo "No valid core specified!"
fi

