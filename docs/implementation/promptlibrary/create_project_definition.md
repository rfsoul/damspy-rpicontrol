**Prompt_ID: reponame create project_definition.md**

Task:
Create or rewrite `docs/setup/project_definition.md` using the earlier project setup documents as source material, and follow the guidance contained in the existing `docs/setup/project_definition.md` file.

Instructions:
1. Read:
   - `docs/setup/short_description.md`
   - `README.md`
   - `docs/setup/project_definition.md` (treat the existing contents as the guideline/template to follow)

2. Produce a completed `docs/setup/project_definition.md`.

Requirements:
- Use `docs/setup/short_description.md` as the original source of truth for the project idea.
- Use `README.md` as the interpreted user-facing description of the project.
- Follow the structure, headings, expectations, and writing rules contained in the current `docs/setup/project_definition.md`.
- Preserve alignment with both the short description and the README.
- Clarify the project boundary more precisely than the README.
- Define what the project is intended to do and what it is not intended to do.
- Identify the intended operating context, users, scope, assumptions, constraints, and non-goals where those can be reasonably inferred.
- Do not invent major features, architecture, workflows, or technical commitments that are not supported by the source documents.
- Do not turn this into a detailed implementation or architecture document.
- Keep the document concrete, disciplined, and decision-useful.

What the finished project definition should achieve:
- define the project purpose clearly
- define the problem or need it addresses
- define the intended scope and boundaries
- define important non-goals or exclusions
- define the operating environment or usage context if known
- make later implementation planning easier by reducing ambiguity

Output requirements:
- Write the final content directly into `docs/setup/project_definition.md`
- Keep the tone clear, professional, and practical
- Prefer explicit boundaries over vague aspirations
- If source information is incomplete, make conservative assumptions only
- Do not include speculative future directions unless the guideline explicitly asks for them

At the end of your response, include:
1. A short summary of what you changed
2. Any assumptions you had to make
3. Any missing, ambiguous, or conflicting information across:
   - `docs/setup/short_description.md`
   - `README.md`
   - `docs/setup/project_definition.md`
