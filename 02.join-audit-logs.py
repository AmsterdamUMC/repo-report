# 02.join-audit-logs.py
# Combines the audit log files into a data frame, written to data/audit-log.tsv
import json, pandas as pd

# Read audit log
df_audit = None
audit_logs = ['data/audit-log.00.json', 'data/audit-log.01.json']
for audit_log in audit_logs:
    audit_json = []
    with open(audit_log, 'r') as f:
        for line in f:
            if line.strip():  # skip empty lines
                audit_json.append(json.loads(line))
    df_current = pd.json_normalize(audit_json)

    # If we already read in audit logs, only add unique events to it
    if (df_audit is None):
        df_audit = df_current
    else:
        df_audit = pd.concat([df_audit, df_current[~df_current['_document_id'].isin(df_audit['_document_id'])]], ignore_index=True)

# Write combined audit log to tsv
df_audit.to_csv('data/audit-log.tsv', sep="\t")
