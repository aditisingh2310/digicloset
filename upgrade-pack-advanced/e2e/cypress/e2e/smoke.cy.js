describe('Smoke Test', () => {
  it('Loads home page', () => {
    cy.visit('/');
    cy.contains('Welcome').should('exist');
  });
});
