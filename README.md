# Python dependencies
Provides two endpoints: 
`https://pydeps.herokuapp.com/{packagename}/{version}`
eg: `https://pydeps.herokuapp.com/matplotlib/3.0.0`

Lists dependencies, and version requirements for them. Downloads
packages to determine their deps on the first query, then uses cached
results for subsequent ones.

`https://pydeps.herokuapp.com/{packagename}}`
eg: `https://pydeps.herokuapp.com/matplotlib/0`

Lists requirements for all versions of a dependency.