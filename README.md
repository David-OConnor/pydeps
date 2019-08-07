# Python dependencies
Provides two endpoints: 
`https://pydeps.herokuapp.com/{packagename}/{version}`
eg: `https://pydeps.herokuapp.com/matplotlib/3.0.0`

`https://pydeps.herokuapp.com/{packagename}}`
eg: `https://pydeps.herokuapp.com/matplotlib/`

Lists dependencies, and version requirements for them. Downloads
packages to determine their deps on the first query, then uses cached
results for subsequent ones.

Uses the `pypi warehouse` to pull avail versions, and to pull deps if listed.
(May change if listed deps prove unreliable. Empty deps lists are always unreliable.)