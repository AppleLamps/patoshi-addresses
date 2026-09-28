-- All output references to selected transactions, all history to frozen watermark.
SELECT i.spent_transaction_hash AS parent_txid, i.spent_output_index AS parent_vout,
 i.transaction_hash AS spending_txid, i.index AS spending_vin,
 i.block_number AS spending_height, CAST(i.block_timestamp AS STRING) AS spending_time
FROM `bigquery-public-data.crypto_bitcoin.inputs` i
WHERE i.spent_transaction_hash IN UNNEST(@txids) AND i.block_number <= 968902
ORDER BY spending_height, spending_txid, spending_vin;
