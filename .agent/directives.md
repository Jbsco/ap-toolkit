# Agentic Maintenance Directives

## Repository Structure
- Core scripts require rigorous review for additions
- Single README with essential information only
- No cross-referencing documentation web
- Additional docs require heavy justification
- Python scripts or other language tools allowed with rigorous review

## Code Standards
- Lightweight bash scripts with embedded help
- Single-line comments only when necessary
- No emojis or fluff in documentation
- Efficient, brief, human readable

## Dependency Management  
- Large applications (KStars, Siril) link to upstream docs
- Test dependencies in script with comments
- Deployment scripts handle installation
- No separate dependency files

## Testing Philosophy
- Scripts test their own dependencies
- `script.sh test` checks prerequisites  
- Use tools baseline functionality uses
- Avoid test complexity exceeding script complexity

## Git Workflow
- Linear history with simple recipe-style commits
- Each commit does one thing only
- Commit messages follow pattern: "if applied this commit will [message]"
- Message format: Capital letter start, no end punctuation, no "and" structure
- Single backquotes for `files` or `commands` acceptable
- Example: "Add Git workflow rules to `.agent/directives.md`"

## Maintenance Priority
- Human usability first
- Lean implementation over features
- Simplification over documentation
- Practical utility over architecture
