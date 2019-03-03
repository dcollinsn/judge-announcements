![License](https://badgen.net/github/license/dcollinsn/judge-announcements)
![Last Commit](https://badgen.net/github/last-commit/dcollinsn/judge-announcements)
[![Dependabot Status](https://api.dependabot.com/badges/status?host=github&repo=dcollinsn/judge-announcements)](https://dependabot.com)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/dcollinsn/judge-announcements.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/dcollinsn/judge-announcements/alerts/)
[![Patreon](https://badgen.net/badge//Support%20me%20on%20Patreon/cyan?icon=patreon)](https://patreon.com/dcollins_judge)
[![Buy me a Coffee?](https://badgen.net/badge/Ko-fi/Buy%20me%20a%20Coffee/cyan)](https://ko-fi.com/dcollins/)

# Judge Announcements
Distributing announcements from the Judge Program far and wide

# Synopsis
This project is an effort to create a system that can find announcements from the Judge Program wherever they might be (JudgeApps, Judge Blogs, ???) and get those announcements to wherever Judges are (Slack, mostly). Users will visit
our web app to configure announcements to Slack teams that they manage. Both the announcement Sources and their Destinations are meant to be modular classes, so more can easily be added in the future.

# Project Status
There's quite a bit of work left to do - basic functionality, UI polish, logging and error handling. Here's something of a summary:

- [x] Push basic messages to Slack
- [ ] Get the "manually entered" announcement type working, start to finish
  - Only certain users can submit each type
  - Web UI to submit announcements
  - Worker tasks create and send messages to configured Destinations
- [ ] Make the Slack message building nicer (with their new "blocks" rich text)
  - [ ] Get a preview image somehow? (Blog or forum post author's avatar?)
- [ ] Web UI to configure announcement routing
- [x] Web UI to create new Slack destinations
  - [ ] It's _working_, but it's ugly.
- [ ] Get announcements from JudgeApps forums
- [ ] Get announcements from Judge Blogs
- [ ] How do we verify that a Slack webhook is valid?
  - Can we verify that the user actually has access to that instance/channel?
  - Can we get the instance/channel name and use it to populate those fields of the Destination?
  - Error handling - what if it stops working?

# Contributing
You can set up something of a local "dev" environment for testing. However, it will have some limitations:
 - No OpenID Connect with JudgeApps (unless you ask me for, and receive, a client ID and a client secret for your dev_settings.py)
   - The steps below create a local superuser account which you log in to with username and password, so JudgeApps OIDC isn't needed.
 - No OAuth2 Slack Workspace connecting (unless you make your own Slack app or ask me for the app secrets, you'll have to get the incoming webhook yourself and add it in the Django admin)
   - You can enter the "Incoming Webhook" directly into the admin page (ask me for the URL), which will allow you to send messages to our testing workspace
   - If you want to test the process of installing a slack instance, then you will have to get the Slack app ID and secret for our testing app, or make your own app at https://api.slack.com/apps

Here's how:
 - Clone this repo into a directory of your choice.
 - Create the file `conf/dev_settings.py` inside the repo with the following content:
   - `from conf.settings import *`
   - `ALLOWED_HOSTS = ('localhost', '127.0.0.1')`
 - Create the VM. `vagrant up`
 - Open two shells into the VM with `vagrant ssh` followed by `sudo su` and `cd /announcements`
 - In one shell, create the database with `python3.7 manage.py migrate`
 - In the same shell, create an account for yourself with `python3.7 manage.py createsuperuser`. I recommend using your JudgeApps username and email, so you can log in to your superuser account with the JudgeApps OIDC provider once you get a client ID and client Secret from me.
 - In the same shell, run the webserver with `python3.7 manage.py runserver 0.0.0.0:8080`
 - In the other shell, run the task loop with `python3.7 manage.py qcluster`
 - Visit `http://127.0.0.1:8087/admin/` in your web browser and log in
 - Create a Manual Source, a Slack Destination, and a Source Routing that links them together.
 - Create a Manual Announcement.
 - Visit `http://192.168.1.6:8087/status/` in your web browser. To speed things up, click "run now" for all three jobs, starting from the top
 - If you set everything up properly, your Manual Announcement should have appeared in the Slack instance you configured as your "Slack Destination"
 - Contact me or open an issue with any questions
