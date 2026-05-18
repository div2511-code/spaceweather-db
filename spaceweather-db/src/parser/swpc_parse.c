/*
 * SWPC fixed-width text parser — implementation stub.
 * Day 4: fill in swpc_parse_line() to match the published column spec for
 *        ace-magnetometer.txt and ace-swepam.txt.
 *
 * Build:  make parser
 * Result: build/libswpc.so — load from Python via ctypes.
 */

#include <ctype.h>
#include <stdio.h>
#include <string.h>

#include "swpc_parse.h"

int swpc_is_header(const char *line) {
    if (line == NULL) return 1;
    while (*line && isspace((unsigned char)*line)) line++;
    if (*line == '\0') return 1;
    if (*line == '#' || *line == ':') return 1;
    return 0;
}

int swpc_parse_line(const char *line, swpc_record_t *out) {
    if (line == NULL || out == NULL) return -1;
    if (swpc_is_header(line)) return -1;

    /* TODO (day 4): the SWPC line format is fixed-width columns:
     *   YR MO DA HHMM Day  Day  S  Bx   By   Bz   Bt   Lat  Lon
     * for the ACE magnetometer feed. Parse those into 'out'.
     * For now this stub just zeroes the struct and returns success
     * so the build pipeline (Makefile + ctypes binding) can be tested
     * end-to-end before the parsing logic is written.
     */
    memset(out, 0, sizeof(*out));
    strncpy(out->timestamp, "1970-01-01T00:00:00Z", sizeof(out->timestamp) - 1);
    return 0;
}
