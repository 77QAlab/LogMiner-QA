Feature: Journey ABC123
  Scenario: Validate journey ABC123
  Given a sanitized transaction journey
  When the system observes login
  Then the compliance checks pass

Feature: Journey fce635cbce150a1628dc0f5be0040b90
  Scenario: Validate journey fce635cbce150a1628dc0f5be0040b90
  Given a sanitized transaction journey
  When the system observes error_event
  Then the compliance checks pass

Feature: Journey 894865d9d0addca346e2b5de331ed9cb
  Scenario: Validate journey 894865d9d0addca346e2b5de331ed9cb
  Given a sanitized transaction journey
  When the system observes fraud_alert
  Then the compliance checks pass