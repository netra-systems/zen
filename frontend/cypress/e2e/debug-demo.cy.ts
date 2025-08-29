/// <reference types="cypress" />

describe('Demo Page Debug', () => {
  it('should visit demo and log page content', () => {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
    
    // Wait for page to load
    cy.wait(5000)
    
    // Log the page title
    cy.title().then((title) => {
      cy.log(`Page title: ${title}`)
    })
    
    // Log visible text
    cy.get('body').then(($body) => {
      const text = $body.text()
      console.log(`Page text: ${text.substring(0, 500)}...`)
    })
    
    // Check if any card elements exist
    cy.get('body').then(($body) => {
      const cards = $body.find('[class*="card"]')
      console.log(`Found ${cards.length} card-like elements`)
      
      const buttons = $body.find('button')
      console.log(`Found ${buttons.length} button elements`)
      
      const divs = $body.find('div')
      console.log(`Found ${divs.length} div elements`)
    })
    
    // Try to find industry text
    cy.get('body').then(($body) => {
      const industryFound = $body.text().includes('Technology')
      console.log(`Technology text found: ${industryFound}`)
      
      const selectIndustryFound = $body.text().includes('Select Your Industry')
      console.log(`Select Your Industry text found: ${selectIndustryFound}`)
      
      // Let's also check the actual HTML
      const html = $body.html()
      console.log(`HTML length: ${html.length}`)
      console.log(`HTML contains "Technology": ${html.includes('Technology')}`)
      console.log(`HTML contains "Financial": ${html.includes('Financial')}`)
      
      // Check if the page is still loading
      const loadingText = $body.text().includes('Loading')
      console.log(`Page showing loading: ${loadingText}`)
    })
    
    // Try specific selectors
    cy.get('h1, h2, h3').then(($headings) => {
      const headingTexts = Array.from($headings).map(h => h.textContent).join(', ')
      console.log(`Found headings: ${headingTexts}`)
    })
    
    // Look for the industry cards specifically
    cy.get('body').should('not.contain', 'Loading')
    
    // Try to wait for specific industry text
    if (Cypress.$('body:contains("Technology")').length > 0) {
      cy.log('Technology found!')
    } else {
      cy.log('Technology NOT found')
      // Let's see what we can find instead
      cy.get('body').find('*:contains("Select")').then(($els) => {
        console.log(`Elements with "Select": ${$els.length}`)
      })
    }
  })
})