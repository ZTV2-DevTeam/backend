// Simple Dark Mode Toggle for Django Admin
(function() {
    'use strict';
    
    // Theme detection and management
    const ThemeManager = {
        init() {
            this.setupThemeDetection();
            this.addThemeToggle();
        },
        
        setupThemeDetection() {
            // Listen for system theme changes
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            
            const handleThemeChange = (e) => {
                // Only auto-switch if no manual preference is set
                if (!localStorage.getItem('admin-theme-preference')) {
                    document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
                }
            };
            
            mediaQuery.addEventListener('change', handleThemeChange);
            
            // Set initial theme
            const savedTheme = localStorage.getItem('admin-theme-preference');
            if (savedTheme) {
                document.documentElement.setAttribute('data-theme', savedTheme);
            } else if (mediaQuery.matches) {
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
            }
        },
        
        addThemeToggle() {
            // Create simple theme toggle button
            // const toggleButton = document.createElement('button');
            // toggleButton.innerHTML = '🌙';
            // toggleButton.setAttribute('aria-label', 'Toggle dark mode');
            // toggleButton.setAttribute('title', 'Toggle dark mode');
            toggleButton.style.cssText = `
                position: fixed;
                top: 15px;
                right: 15px;
                background: var(--admin-primary-color);
                color: white;
                border: none;
                border-radius: 4px;
                width: 40px;
                height: 40px;
                font-size: 16px;
                cursor: pointer;
                z-index: 9999;
            `;
            
            toggleButton.addEventListener('click', () => {
                const currentTheme = document.documentElement.getAttribute('data-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                
                document.documentElement.setAttribute('data-theme', newTheme);
                localStorage.setItem('admin-theme-preference', newTheme);
                
                // Update button icon
                toggleButton.innerHTML = newTheme === 'dark' ? '☀️' : '🌙';
            });
            
            // Update button based on current theme
            const currentTheme = document.documentElement.getAttribute('data-theme');
            if (currentTheme === 'dark') {
                toggleButton.innerHTML = '☀️';
            }
            
            document.body.appendChild(toggleButton);
        }
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            ThemeManager.init();
        });
    } else {
        ThemeManager.init();
    }
})();
