# Changelog
All notable changes to this project will be documented in this file from v1.0.2.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]
### Fixed
- Fixed bug where competency disappears from dashboard if all subsections are marked as fail

## [1.0.2] - 2021-10-01
### Fixed
- Fixed bug where page errors if no subsections or inactive subsections are selected for evidence upload
- Fixed bug where date picker wasn't rendering

## [1.0.1] - 2021-09-21
### Added
- Informative error message when obsolete documents are linked to a competency.

### Fixed
- Fixed bug where document names weren't rendering in competency downloads

## [1.0.0] - 2021-08-25
### Added
- Service reports page to monitor trends over time
- Service overview page for Head of Service to monitor overall training

### Changed
- User reports page now accessible by anyone
- Training status now available for all comeptencies
- Admins can now sign off anyone for reassessments
- Finished upgrade of coding language from Python 2 to Python 3
- Updated base docker from Python 2 to Python 3

### Fixed
- Multiple files can now be uploaded as evidence at one time