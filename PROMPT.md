# Prompts

These are the prompts used with **Gemma-3-1B** (`google/gemma-3-1b-it`) in `extractor.py`.
`{document_text}` is replaced with a chunk of the CIS benchmark (its recommendation lines,
e.g. `4.1 Ensure that a user for the container has been created`).

## zero-shot

```
You are a security analyst. Read the security requirements document below and identify its key data elements.
A key data element is a configuration item, component or setting that the requirements talk about (for example: container user, image, port, log file).
One key data element can map to several requirements.

Answer only with YAML in exactly this format and nothing else:
element1:
  name: <short name of the key data element>
  requirements:
    - <requirement text>
    - <requirement text>
element2:
  name: <short name of the key data element>
  requirements:
    - <requirement text>

Document:
{document_text}
```

## few-shot

```
You are a security analyst. Identify the key data elements in a security requirements document.
A key data element is a configuration item, component or setting that the requirements talk about.
One key data element can map to several requirements.

Example document:
4.1 Ensure that a user for the container has been created
4.6 Ensure that HEALTHCHECK instructions have been added to container images
4.9 Ensure that COPY is used instead of ADD in Dockerfiles
5.4 Ensure that privileged containers are not used
5.25 Ensure that the container is restricted from acquiring additional privileges

Example answer:
element1:
  name: container user
  requirements:
    - Ensure that a user for the container has been created
element2:
  name: healthcheck instruction
  requirements:
    - Ensure that HEALTHCHECK instructions have been added to container images
element3:
  name: copy instruction
  requirements:
    - Ensure that COPY is used instead of ADD in Dockerfiles
element4:
  name: container privileges
  requirements:
    - Ensure that privileged containers are not used
    - Ensure that the container is restricted from acquiring additional privileges

Now do the same for the document below. Answer only with YAML in the same format and nothing else.

Document:
{document_text}
```

## chain-of-thought

```
You are a security analyst. Identify the key data elements in the security requirements document below.
A key data element is a configuration item, component or setting that the requirements talk about.
One key data element can map to several requirements.

Think step by step:
Step 1: List every requirement in the document (lines such as "Ensure that ...").
Step 2: For each requirement, decide which configuration item, component or setting it is about.
Step 3: Group requirements that are about the same item under one key data element.
Step 4: Write the result as YAML in exactly this format:
element1:
  name: <short name of the key data element>
  requirements:
    - <requirement text>
    - <requirement text>
element2:
  name: <short name of the key data element>
  requirements:
    - <requirement text>

After your reasoning, write the final YAML after a line that says FINAL ANSWER:

Document:
{document_text}
```
