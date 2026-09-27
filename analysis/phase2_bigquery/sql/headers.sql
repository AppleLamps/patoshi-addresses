SELECT b.number AS height, b.hash AS block_hash, b.version, b.merkle_root,
  CAST(b.timestamp AS STRING) AS timestamp, b.nonce, b.bits,
  b.coinbase_param, b.transaction_count
FROM `bigquery-public-data.crypto_bitcoin.blocks` AS b
WHERE b.number BETWEEN 0 AND 54619
ORDER BY b.number;
