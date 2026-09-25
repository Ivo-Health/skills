---
name: patient-data-protection
description: Use when writing or reviewing code, tests, fixtures, logs, commits, tickets, prompts or documents at Ivo Health that could involve patient information, or when someone shares data that might identify a patient. Keeps patient-identifiable information out of code and AI tools.
---

# Patient data protection

Ivo Health builds software for hospital at home teams. Patient-identifiable information must only ever be in the systems approved to hold it. It must never be in our code, our tooling or conversations with AI tools.

## What counts as patient-identifiable

Treat these as identifiable, on their own or combined:

- NHS number, hospital number or any other patient identifier
- name, address, postcode, date of birth, phone number or email address
- photos, scans or free-text clinical notes
- details that could identify someone when combined, such as a rare condition and a small area

If you are not sure, treat it as identifiable.

## Rules

1. Never put real patient information in code, tests, fixtures, seed data, logs, error messages, analytics events, commit messages, branch names, pull requests, tickets or prompts.
2. Use synthetic data only:
   - generate NHS-number-shaped values in code at test time, rather than writing them into files
   - use `example.com` email addresses
   - use Ofcom drama phone numbers, such as 07700 900123
   - use names that are obviously made up
3. Log internal identifiers, such as database IDs, rather than NHS numbers or names. Do not log request or response bodies that may contain patient data.
4. Use the minimum information needed for the task, and be able to say why it is needed (Caldicott Principles 1 to 3).
5. Do not copy production data into development, test or demo environments.

## If someone shares real patient information

1. Stop. Do not repeat the information or write it to any file.
2. Tell them it looks like real patient information and should be removed from the conversation or file.
3. Point them to the incident steps in `SECURITY.md` in the `Ivo-Health/skills` repository.

## When reviewing a change

Check for:

- identifiers in logs
- real-looking data in fixtures
- data sent to third-party services
- new fields that store patient data without a clear purpose

Raise anything you find before the change is merged.

## Sources

- The Caldicott Principles (UK Caldicott Guardian Council and Department of Health and Social Care): https://www.gov.uk/government/publications/the-caldicott-principles
- UK GDPR guidance (Information Commissioner's Office): https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/
- Data Security and Protection Toolkit (NHS England): https://www.dsptoolkit.nhs.uk/
- NHS number format (NHS Data Model and Dictionary): https://www.datadictionary.nhs.uk/attributes/nhs_number.html
- Numbers for drama (Ofcom): https://www.ofcom.org.uk/phones-and-broadband/phone-numbers/numbers-for-drama
