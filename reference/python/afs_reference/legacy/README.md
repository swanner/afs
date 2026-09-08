# PackML 0.1 Compatibility Adapter

This `legacy/` package retains the command-based `PackMLLifecycle` as the 0.1
compatibility adapter for the published 0.1 examples. Its Unit and State Machine
example and Parent/Subunit composition adapter remain executable and covered by
tests.

Parent/Subunit composition remains part of the accepted AFS direction and the
draft AFS Unit Composition specification. Its executable reference currently
uses this compatibility adapter because the declarative `PackMLMachine`
reference does not yet provide a Parent/Subunit adapter.

For new implementations, the component-based `PackMLMachine` in the parent
package is the preferred current lifecycle runtime. A Unit must never run both
lifecycle implementations as authorities.

Run the compatibility example from the repository root with:

```bash
python -m reference.python.afs_reference.legacy
```
