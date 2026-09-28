SELECT t.hash AS txid, t.block_number AS height,
 CAST(t.block_timestamp AS STRING) AS block_timestamp,
 t.version, t.lock_time, t.input_count, t.output_count,
 CAST(t.input_value AS STRING) AS input_value,
 CAST(t.output_value AS STRING) AS output_value,
 TO_JSON_STRING(t.inputs) AS inputs_json, TO_JSON_STRING(t.outputs) AS outputs_json
FROM `bigquery-public-data.crypto_bitcoin.transactions` t
WHERE t.hash IN UNNEST(@txids) AND t.block_number <= 968902
 AND t.block_timestamp >= TIMESTAMP(@start) AND t.block_timestamp <= TIMESTAMP(@end)
ORDER BY height, txid;
