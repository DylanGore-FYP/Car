# Car

<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-2-orange.svg?style=for-the-badge)](#contributors)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/DylanGore-FYP/Car/Lint%20Code?label=Lint%20Status&logo=github&style=for-the-badge)](https://github.com/DylanGore-FYP/Car/actions/workflows/lint.yml)

This software is intended to run on a device located within a vehicle and can poll data from the OBD-II port and GNSS. The default output for this data is via MQTT but a new output plugin can be created if required.

## Configuration

Please create a configuration file called `config.toml` and modify it to suit your needs. An example is included in the repository.

## Running

To run this software, you need `pipenv`.

```bash
pip3 install pipenv
```

Once `pipenv` is installed run:

```bash
pipenv install
```

to create a virtual environment and install all the requirements

followed by:

```bash
pipenv run python3 -m car
```

to run the code.

## Deployment

For instructions on how to setup and configure a Raspberry Pi to run this software, please see the relevant [documentation page](https://dylangore-fyp.github.io/Documentation/setup/vehicle/).

## Commit Message Convention

This project uses [Gitmoji](https://gitmoji.dev/) for commit organisation. For more details see the [Gitmoji Repository](https://github.com/carloscuesta/gitmoji).

## Contributors

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://github.com/DylanGore"><img src="https://avatars.githubusercontent.com/u/2760449?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Dylan Gore</b></sub></a><br /><a href="https://github.com/DylanGore-FYP/Car/commits?author=DylanGore" title="Code">💻</a> <a href="https://github.com/DylanGore-FYP/Car/commits?author=DylanGore" title="Documentation">📖</a> <a href="#ideas-DylanGore" title="Ideas, Planning, & Feedback">🤔</a></td>
    <td align="center"><a href="https://github.com/mohittaneja7"><img src="https://avatars.githubusercontent.com/u/4126813?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Mohit Taneja</b></sub></a><br /><a href="#ideas-mohittaneja7" title="Ideas, Planning, & Feedback">🤔</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification.
