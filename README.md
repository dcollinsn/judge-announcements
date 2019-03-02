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
- [ ] Web UI to configure announcement routing
- [ ] Web UI to create new Slack destinations
- [ ] Get announcements from JudgeApps forums
- [ ] Get announcements from Judge Blogs
- [ ] How do we verify that a Slack webhook is valid?
  - Can we verify that the user actually has access to that instance/channel?
  - Can we get the instance/channel name and use it to populate those fields of the Destination?
  - Error handling - what if it stops working?
