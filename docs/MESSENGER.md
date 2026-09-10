# Messenger

The 0.8.0 pilot implements optional one-to-one text conversations between
confirmed friends. Attachments, public rooms and group conversations are not
included. Blocking or removing a friendship closes conversation access.

Messages use browser cryptography. The current account-based recovery design
is not operator-blind encryption and has not received an independent security
audit. Do not advertise it as a fully accepted secure messaging service.

Fresh-browser restoration and real two-user messaging require functional
acceptance. See [release notes](RELEASE-0.8.0.md) and
[recovery phases](CHAT-RECOVERY-PHASES.md). Operational configuration is kept
separately from this public documentation.
