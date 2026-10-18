# Form filling check

This is a small engineering check on the bundled sample form. It is not a public benchmark.

## Form

`examples/sample-form.pdf` has 11 AcroForm fields:

- first name, last name, email, phone
- address, city, state, ZIP, country
- date of birth
- terms checkbox

The profile has 10 personal values. The checkbox is set by hand.

## Method

1. Inspect the PDF with pypdf.
2. Match each field name with the alias table.
3. Fill text fields and the checkbox.
4. Read the values back from the output PDF.
5. Render a preview and test flattening.

## Results

- 10 of 10 profile fields matched a form field.
- 11 of 11 fields were filled, including the checkbox as `/Yes`.
- The output PDF reopened with the correct values.
- The preview rendered at 918x1188.
- Flattening produced a one-page PDF.

## Caveats

- Field names in the sample are clean. Real forms use names like `form1[0].Page1[0].Name[0]`, which still normalize but may need manual overrides.
- There is no scanned-form test. AcroForm only.
- The mapping is deterministic and explainable, not an LLM guess.

## Commands

```bash
formwise fields examples/sample-form.pdf
formwise fill examples/sample-form.pdf --profile examples/profile.json -o /tmp/filled.pdf
```


## Encryption check

- `formwise profile --encrypt` wrote a 550-byte envelope with mode 600.
- The plaintext name `Jane` was not present in the file.
- Loading without a passphrase raised `ProfileLocked`.
- Loading with the correct passphrase returned the values.
- Loading with a wrong passphrase was rejected.
- Filling the sample form from the encrypted profile succeeded with 10 fields.


## Batch check

- Two generated forms were filled from one profile.
- Both outputs were written and both reported two filled fields.
- The audit file was mode 600 and contained field counts and profile keys only.
- The value `Jane` and the email address were not present in the audit file.

## Scanned-field detection

A generated scanned-style PDF with `Name:`, `Email:`, `Phone:`, and `Address:` labels produced four proposals through RapidOCR. Each proposal was placed below the label, and one filled value was stamped into the downloaded PDF.

Detection is a proposal, not a guarantee. Unusual labels, handwriting, and rotated pages can be missed. Only the first page is detected automatically; additional pages use manual placement.
