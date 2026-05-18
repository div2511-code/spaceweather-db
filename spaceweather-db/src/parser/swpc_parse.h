/*
 * SWPC fixed-width text parser — header.
 * Format spec: https://services.swpc.noaa.gov/text/ace-magnetometer.txt
 * (Header lines start with '#' or ':'; data rows are whitespace-separated.)
 */

#ifndef SWPC_PARSE_H
#define SWPC_PARSE_H

typedef struct {
    char   timestamp[32];   /* "YYYY-MM-DDThh:mm:ssZ" */
    double bz_gsm;          /* nT — sentinel -999.9 = missing */
    double bt;              /* nT */
    double speed_kmps;
    double density_pcc;
    double temperature_k;
} swpc_record_t;

/* Parse a single non-header line into 'out'. Returns 0 on success, -1 on failure. */
int swpc_parse_line(const char *line, swpc_record_t *out);

/* Returns 1 if the line is a header/comment (starts with '#', ':' or blank). */
int swpc_is_header(const char *line);

#endif /* SWPC_PARSE_H */
