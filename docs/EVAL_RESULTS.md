# Evaluation Results - fastText MVP (2026-02-02)

## Dataset
- Training: 1346 samples (80%)
- Validation: 337 samples (20%)
- Classes: scam (crypto_scam), clean

## Confusion Matrix

```
                  Predicted
                  scam    clean
Actual scam       145     32
Actual clean      19      141
```

## Per-Class Metrics

| Class | Precision | Recall | F1 Score |
|-------|-----------|--------|----------|
| SCAM  | 0.884     | 0.819  | 0.850    |
| CLEAN | 0.815     | 0.881  | 0.847    |

## Key Metrics

- **False Positive Rate**: 19/160 = **11.9%** (clean posts flagged as scam)
- **False Negative Rate**: 32/177 = **18.1%** (scams that slip through)

## False Positives Analysis

These are legitimate posts that got incorrectly flagged as scam:

1. `be aware of scammers! coinmarketcap will never dm you first...` - Warning about scams (ironic!)
2. `if your project has a token it can get distribution...` - Legitimate project post
3. `gm ct ☀️ connect wallet & x do socials...` - Has "connect wallet" but appears legit
4. `just checked the link your sharing looks pretty interesting...` - Normal reply
5. `ok send me all your crypto in that case:)))` - Sarcastic joke
6. `reporting will be posted on gov.optimism.io...` - Official Optimism governance
7. `ok guys its super late im gonna work some bags...` - "bags" triggered it
8. `we're powering the @weex_official ai wars finals...` - Exchange promo (borderline)
9. `month to date basket returns ai 29.64%...` - Market data
10. `♡︎ this if i can send you a bnwo wallpaper...` - Unrelated post

## Observations

1. **11.9% FP rate is too high** for production - users would see ~1 in 8 legit posts hidden
2. Model triggers on keywords like: "wallet", "connect", "claim", "bags", "airdrop"
3. Some FPs are borderline (exchange promos) - labeling might need review
4. Need to tune threshold or add more clean samples with crypto keywords

## Next Steps

1. **Threshold tuning**: Raise confidence threshold to reduce FPs
2. **More clean data**: Add more legitimate crypto posts with "scammy" keywords
3. **Hard negative mining**: Find clean posts the model gets wrong, add to training
4. **Char n-grams**: Add character-level features to catch l33tspeak
