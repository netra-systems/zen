#!/usr/bin/env node
/**
 * Test Staging WebSocket Protocol Verification
 * 
 * Purpose: Verify that the staging deployment now sends the correct WebSocket 
 *          protocol format ['jwt-auth', 'jwt.{encodedToken}'] instead of broken format.
 * 
 * Issue: #171 - Frontend/backend WebSocket protocol mismatch causing 1011 errors
 * Expected: ['jwt-auth', 'jwt.{base64url_encoded_token}']
 */

const https = require('https');
const url = require('url');

const STAGING_URL = 'https://netra-frontend-staging-pnovr5vsba-uc.a.run.app';

console.log('🚀 Testing Staging WebSocket Protocol Format');
console.log('=' .repeat(60));
console.log(`Target: ${STAGING_URL}`);
console.log('Expected Protocol: [\'jwt-auth\', \'jwt.{encodedToken}\']');
console.log('=' .repeat(60));

// Fetch the main page and extract JavaScript bundle URLs
function fetchMainPage() {
    return new Promise((resolve, reject) => {
        https.get(STAGING_URL, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                // Extract script src URLs
                const scriptMatches = data.match(/<script[^>]+src="([^"]+)"/g);
                const scripts = scriptMatches ? scriptMatches.map(match => {
                    const srcMatch = match.match(/src="([^"]+)"/);
                    return srcMatch ? srcMatch[1] : null;
                }).filter(Boolean) : [];
                
                console.log(`📋 Found ${scripts.length} script bundles:`);
                scripts.forEach((script, i) => {
                    const fullUrl = script.startsWith('http') ? script : `${STAGING_URL}${script}`;
                    console.log(`   ${i+1}. ${script}`);
                });
                
                resolve(scripts);
            });
        }).on('error', reject);
    });
}

// Check each script bundle for WebSocket protocol format
async function checkBundleForWebSocketCode(scriptUrl) {
    return new Promise((resolve, reject) => {
        const fullUrl = scriptUrl.startsWith('http') ? scriptUrl : `${STAGING_URL}${scriptUrl}`;
        
        https.get(fullUrl, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                // Search for WebSocket protocol patterns
                const jwtAuthPattern = /jwt-auth/g;
                const jwtProtocolPattern = /jwt\.\${[^}]+}/g;
                const protocolsPattern = /protocols\s*=\s*\[[^\]]*\]/g;
                
                const jwtAuthMatches = data.match(jwtAuthPattern) || [];
                const jwtProtocolMatches = data.match(jwtProtocolPattern) || [];
                const protocolsMatches = data.match(protocolsPattern) || [];
                
                resolve({
                    url: scriptUrl,
                    jwtAuthCount: jwtAuthMatches.length,
                    jwtProtocolCount: jwtProtocolMatches.length,
                    protocolsArrays: protocolsMatches,
                    hasWebSocketCode: jwtAuthMatches.length > 0 || jwtProtocolMatches.length > 0 || protocolsMatches.length > 0
                });
            });
        }).on('error', (err) => {
            console.log(`⚠️  Failed to fetch ${scriptUrl}: ${err.message}`);
            resolve({ url: scriptUrl, hasWebSocketCode: false, error: err.message });
        });
    });
}

// Main execution
async function main() {
    try {
        console.log('📦 Step 1: Fetching main page and extracting script bundles...');
        const scripts = await fetchMainPage();
        
        if (scripts.length === 0) {
            console.log('❌ No script bundles found in main page');
            return;
        }
        
        console.log('\n🔍 Step 2: Analyzing JavaScript bundles for WebSocket protocol code...');
        
        let foundWebSocketCode = false;
        
        for (const script of scripts) {
            const result = await checkBundleForWebSocketCode(script);
            
            if (result.hasWebSocketCode) {
                foundWebSocketCode = true;
                console.log(`\n✅ Found WebSocket code in: ${result.url}`);
                console.log(`   - 'jwt-auth' occurrences: ${result.jwtAuthCount}`);
                console.log(`   - 'jwt.\${...}' patterns: ${result.jwtProtocolCount}`);
                
                if (result.protocolsArrays && result.protocolsArrays.length > 0) {
                    console.log(`   - Protocols arrays found: ${result.protocolsArrays.length}`);
                    result.protocolsArrays.forEach((arr, i) => {
                        console.log(`     ${i+1}. ${arr.substring(0, 100)}...`);
                    });
                }
            }
        }
        
        if (!foundWebSocketCode) {
            console.log('\n⚠️  No WebSocket protocol code found in any bundle');
            console.log('   This could mean the code is dynamically loaded or minified beyond recognition');
        }
        
        console.log('\n📊 Protocol Format Verification Summary:');
        console.log('=' .repeat(60));
        
        if (foundWebSocketCode) {
            console.log('✅ WebSocket-related code found in deployed bundle');
            console.log('✅ Ready for runtime protocol format testing');
            console.log('\n🎯 Next Step: Test actual WebSocket connection to verify protocol format');
        } else {
            console.log('⚠️  WebSocket code not detected in static analysis');
            console.log('   Deployment may be successful, but requires runtime testing');
        }
        
    } catch (error) {
        console.error('❌ Error during verification:', error);
    }
}

main();