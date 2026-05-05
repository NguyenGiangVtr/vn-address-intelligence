#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

/**
 * Build Version Manager for VN Address Intelligence
 * Automatically updates version numbers in HTML files for cache busting
 */

// Generate version string (timestamp or git hash)
function generateVersion() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hour = String(now.getHours()).padStart(2, '0');
    const minute = String(now.getMinutes()).padStart(2, '0');
    
    return `${year}${month}${day}${hour}${minute}`;
}

// Update version in HTML file
function updateVersionInFile(filePath, version) {
    try {
        let content = fs.readFileSync(filePath, 'utf8');
        
        // Update CSS version
        content = content.replace(
            /style\.css\?v=\d+/g, 
            `style.css?v=${version}`
        );
        
        // Update JS version 
        content = content.replace(
            /app\.js(\?v=\d+)?/g,
            `app.js?v=${version}`
        );
        
        // Add version to other assets if needed
        content = content.replace(
            /(src|href)="([^"]*\.(js|css))(\?v=\d+)?"/g,
            (match, attr, file, ext) => {
                // Skip external URLs
                if (file.startsWith('http') || file.includes('cdnjs') || file.includes('jsdelivr')) {
                    return match;
                }
                return `${attr}="${file}?v=${version}"`;
            }
        );
        
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`✓ Updated ${path.basename(filePath)} with version ${version}`);
        
    } catch (error) {
        console.error(`✗ Error updating ${filePath}:`, error.message);
    }
}

// Find all HTML files
function findHtmlFiles(dir) {
    const files = [];
    
    function scan(currentDir) {
        const items = fs.readdirSync(currentDir);
        
        for (const item of items) {
            const fullPath = path.join(currentDir, item);
            const stat = fs.statSync(fullPath);
            
            if (stat.isDirectory()) {
                scan(fullPath);
            } else if (item.endsWith('.html')) {
                files.push(fullPath);
            }
        }
    }
    
    scan(dir);
    return files;
}

// Main execution
function main() {
    const version = generateVersion();
    const uiDir = path.join(__dirname, 'ui');
    
    console.log(`\n🚀 Building with version: ${version}\n`);
    
    if (!fs.existsSync(uiDir)) {
        console.error('❌ UI directory not found!');
        process.exit(1);
    }
    
    const htmlFiles = findHtmlFiles(uiDir);
    
    if (htmlFiles.length === 0) {
        console.log('⚠️  No HTML files found');
        return;
    }
    
    htmlFiles.forEach(file => {
        updateVersionInFile(file, version);
    });
    
    // Write version info for reference
    const versionInfo = {
        version: version,
        timestamp: new Date().toISOString(),
        files_updated: htmlFiles.map(f => path.relative(__dirname, f))
    };
    
    fs.writeFileSync(
        path.join(__dirname, 'version-info.json'), 
        JSON.stringify(versionInfo, null, 2)
    );
    
    console.log(`\n✅ Build completed! Updated ${htmlFiles.length} HTML files`);
    console.log(`📝 Version info saved to version-info.json`);
}

// Run if called directly
if (require.main === module) {
    main();
}

module.exports = { generateVersion, updateVersionInFile };