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
