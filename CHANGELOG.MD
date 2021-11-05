# Changelog
All notable changes to this project will be documented in this file from v1.0.0.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [1.1.0] - 2021-11-05
### Added
- Added the ability to mark competencies as not required. Where this applies, training is showed as "Partially trained" 
  on dashboard and in reports
- New versions of a competence now inherit evidence from previous versions
### Changed
- Lists of trainers and authorisers are now alphabetical
- Reset password links removed from login page and dashboard (Note: code is commented out and can be reinstated)
- Changed logic for deciding buttons on view competence page, improved button appearance
- Improved appearance of competency report downloads
### Fixed
- Fixed bug where competency disappears from dashboard if all subsections are marked as fail
- Fixed bug where document names weren't rendering in competency edit page
- Fixed bug where edit page wouldn't render for competencies with no associated q-pulse documents
- Competency reports webpage and download now show the same numbers

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
- Training status now available for all competencies
- Admins can now sign off anyone for reassessments
- Finished upgrade of coding language from Python 2 to Python 3
- Updated base docker from Python 2 to Python 3
### Fixed
- Multiple files can now be uploaded as evidence at one time