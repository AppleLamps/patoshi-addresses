-- Exact P2PKH script matching avoids BigQuery's synthetic P2PK address labels.
-- Equivalent to intersecting the target addresses with the entire P2PKH UTXO set.
-- Historical spent matches retained to distinguish funding/reuse from true collisions.
WITH matched AS (
 SELECT o.transaction_hash AS txid, o.index AS vout, o.block_number AS height,
 o.script_hex, CAST(o.value AS STRING) AS value_sats
 FROM `bigquery-public-data.crypto_bitcoin.outputs` o
 WHERE o.script_hex IN UNNEST(@scripts) AND o.block_number <= 968902
)
SELECT m.*, i.transaction_hash AS spending_txid, i.block_number AS spending_height,
 i.script_hex AS spending_scriptsig
FROM matched m
LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
 ON i.spent_transaction_hash=m.txid AND i.spent_output_index=m.vout
 AND i.block_number <= 968902
ORDER BY height, txid, vout;
