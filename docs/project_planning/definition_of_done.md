# Definition of Done (DoD) for Sentimark Tasks

## Overview
The Definition of Done (DoD) is a clear and concise list of requirements that a task must satisfy to be considered complete. This ensures consistency, quality, and completeness across all work items in the Sentimark project. The DoD is integrated with our automated Kanban system to track progress, evidence of completion, and next steps.

## Task Completion Criteria

### Code Quality
- All code follows the project's style guide and coding standards
- Code is properly formatted according to project conventions
- No compiler warnings or linting errors
- All public methods, classes, and functions are documented

### Testing
- Unit tests written for all new functionality
- Integration tests added for component interactions
- All tests pass successfully
- Test coverage meets or exceeds project standards
- Edge cases and error conditions are tested

### Verification
- Functionality works as expected in CLI environment
- Verification steps documented and executable by others
- CLI commands provided to validate functionality
- Performance meets requirements

### Documentation
- Code is properly documented with comments
- README or relevant documentation updated
- API documentation updated if applicable
- Usage examples provided for new features

### Error Handling
- Proper error handling implemented
- Edge cases considered and handled
- Appropriate logging implemented
- Failure scenarios documented

### Security
- Security best practices followed
- Input validation implemented
- Authentication/authorization checks in place where needed
- No sensitive data exposed

### Review
- Code review completed by at least one other team member
- Feedback addressed and incorporated
- No outstanding review comments

### Automated Kanban Integration

- All tasks must be tracked in the CLI Kanban board
- Task status must be updated automatically when possible
- Evidence of completion must be captured and stored in the Kanban
- Next steps must be clearly identified after task completion

### Evidence Format

When completing a task, evidence must be provided in the following format:

```
TASK-EVIDENCE: [Brief summary of what was done] - Verified with [specific CLI commands or verification steps]
```

This format is critical as it's used by the automated system to update the Kanban board. Claude will always include this line at the end of its responses when completing a task.

#### Examples:
```
TASK-EVIDENCE: Implemented PostgreSQL repository with CRUD operations - Verified with 'curl -X POST http://localhost:3000/api/records' and 'SELECT * FROM sentiment_records'
```

```
TASK-EVIDENCE: Added JWT authentication to API endpoints - Verified with 'curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/protected' returning 200 OK
```

```
TASK-EVIDENCE: Implemented sentiment analysis caching - Verified with 'time python test_cache.py' showing 95% reduction in processing time for repeated queries
```

## Automated Workflow

### 1. Task Creation and Assignment

1. Tasks are created in the Kanban board using the CLI tool
2. Each task includes a title, description, and type
3. Tasks start in the "Project Backlog" column

### 2. Task Processing with Claude

1. Use the `auto-claude.sh` script to process a task with Claude
2. The script automatically moves the task to "In Progress"
3. Claude works on the task and provides implementation and verification steps
4. Claude includes the TASK-EVIDENCE line at the end of its response
5. The script extracts this line and updates the Kanban board
6. Task is automatically moved to "Needs Review"

### 3. Task Review and Completion

1. Review the task implementation and evidence
2. Run the verification steps to confirm functionality
3. If acceptable, move the task to "Done"
4. If changes are needed, provide feedback and move back to "In Progress"

### 4. Continuous Improvement

1. Regularly review completed tasks for patterns and improvements
2. Update the Definition of Done as needed
3. Refine the automation process based on team feedback

This automated workflow ensures consistent task tracking, clear evidence of completion, and visibility into project progress at all times.

This evidence will be stored in the Kanban board and used to verify that the task meets the Definition of Done.
