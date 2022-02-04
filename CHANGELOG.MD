# Changelog
All notable changes to this project will be documented in this file from v1.0.0.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Reassessments: added capacity for four year reassessments including new evidence submission
- Added error handling for 502 errors
- Daily cron job to flag competencies that have reached their four year expiry
- Emails are now sent when reassessments are submitted, accepted or rejected
- Emails are now sent when expiry and four year expiry dates are at 30 days before, 7 days before and expired
### Fixed
- Homepage: 'assigned by' now shows assigner, not user
### Changed
- CPD: Updated CPD event name to 200 characters

## [v1.2.2] - 2022-01-06
### Fixed
- Reassessments: submission error fixed

## [v1.2.1] - 2022-01-05
### Fixed
- CPD module: download now works in docker
- Homepage: correct version competence title now displays

## [v1.2.0] - 2022-01-04
### Added
- New 'Action Required By' column for Assigned and In Progress competencies table on homepage
- Character counters added to discussion and observation fields in evidence upload page
- CPD module: events can now be edited
- CPD module: CPD log can now be downloaded as a csv
### Fixed
- Four year due competencies now show in 'complete' section on dashboard
- Fixed bug where competencies could not be edited if originally created with no linked documents and then had documents added
### Changed
- Reassessments now require all complete subsections to be reassessed simultaneously
- Assessment date override now overrides completed date instead of expiry date

## [1.1.1] - 2021-11-14
### Fixed
- Assigned date no longer stuck on day of app deployment
### Changed
- Activate button now "Activate Training"
- Submit Evidence button now shows if competence is Failed
=========
## [Unreleased]
### Fixed
- Four year due competencies now show in 'complete' section on dashboard
>>>>>>>>> Temporary merge branch 2

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