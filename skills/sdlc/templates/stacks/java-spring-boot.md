Enforce via tooling, not here: formatting → Spotless (google-java-format);
static analysis → Checkstyle + SpotBugs/PMD, wired into the Maven build.

1. Controllers validate the request DTO with `@Valid` + Bean Validation
   annotations; a service method never re-validates what the controller
   boundary already checked.
2. Business rules live in the service layer; a controller translates
   HTTP <-> domain and never branches on domain state.
3. The transaction boundary is the service method (`@Transactional`), never
   the repository or the controller; a repository method is not itself
   `@Transactional` unless it composes multiple writes on its own.
4. Entities are never returned directly from a controller; map to a
   response DTO — this is what keeps JPA lazy-loading and JSON
   serialization from fighting each other.
5. Integration tests run against the real engine via Testcontainers;
   mocking the database (`@MockBean` on a repository) is banned in
   integration tests — it does not catch the SQL bugs that matter.
6. Unit tests (JUnit 5 + Mockito) target one class with its collaborators
   mocked; a test that needs a Spring context is an integration test, named
   and located accordingly, not a unit test.
7. Exceptions crossing the service→controller boundary are domain
   exceptions, translated to HTTP status by one `@ControllerAdvice` — no
   `try/catch` producing an ad hoc `ResponseEntity` per controller.
8. A `@Transactional` method never calls an external HTTP or queue client
   inside the transaction; dispatch that call after commit (event listener,
   outbox) so a slow downstream never holds a database lock.
9. Migrations are Flyway scripts, one per change, forward-only; never edit
   a migration that already ran in any shared environment.
10. Constructor injection only, no field `@Autowired` — it makes required
    dependencies explicit and the class constructible in a plain unit test.
11. A JPA relationship defaults to `LAZY`; `EAGER` requires a comment naming
    the query pattern that needs it.
12. Table-driven tests (`@ParameterizedTest` + `@MethodSource`) for any
    method with more than two branch conditions, instead of copy-pasted
    per-case tests.
13. Package by feature (`payments`, `bookings`), not by layer
    (`controllers`, `services`, `repositories`) — a feature's files stay
    next to each other.
14. Configuration is bound to typed `@ConfigurationProperties` classes,
    never scattered `@Value("${...}")` injections across unrelated beans.
