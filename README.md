# Python dependencies
Example API calls: `https://pydeps.herokuapp.com/requests`, 
`https://pydeps.herokuapp.com/requests/2.21.0`. 
This pulls all top-level
dependencies for the `requests` package, and the dependencies for version `2.21.0` respectively.
There is also a `POST` API for pulling info on specified versions.
 The first time this command is run
for a package/version combo, it may be slow. Subsequent calls, by anyone,
should be fast. This is due to having to download and install each package
on the server to properly determine dependencies, due to unreliable information
 on the `pypi warehouse`.