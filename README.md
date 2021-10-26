# Juju SNMPD subordinate charm

This subordinate charm will deploy snmpd

## Usage

```
juju deploy snmpd
juju add-relation ubuntu snmpd
```

To retrieve the configured pass phrases, run the below commands, 
```
juju run-action --wait snmpd/X show-auth-pass-phrase
juju run-action --wait snmpd/X show-priv-pass-phrase
```

### Note:-
1. Pass phrases can be updated either as an option or as include-file in the YAML format.

```
  snmpv3_pass_phrase:
    default: |
      ---
      auth_pass_phrase: "auth_password"
      priv_pass_phrase: "priv_password"
    description: |
      Define the default authentication and privacy pass phrases to use for SNMPv3 requests.
      example (using include-file):
        snmpv3_pass_phrase: include-file://snmpd_pass_phrase.yaml
```

2. Irrespective of the previous ```security_name```, it creates new user but pass phrases can be updated for the same user.
    
    Ex: If you changed the pass phrases for the same user, previous pass phrases never work, but works with the latest supplied pass phrases.
