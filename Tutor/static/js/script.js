document.addEventListener('DOMContentLoaded', function() {
    const studyGuideForm = document.getElementById('studyGuideForm');
    const resultContainer = document.getElementById('resultContainer');
    const studyGuideContent = document.getElementById('studyGuideContent');
    const loadingElement = document.getElementById('loading');
    const downloadBtn = document.getElementById('downloadBtn');
    
    let currentFilename = null;
    
    // Form submission handler
    studyGuideForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Show loading state
        resultContainer.style.display = 'block';
        studyGuideContent.style.display = 'none';
        loadingElement.style.display = 'flex';
        loadingElement.querySelector('p').textContent = 'Generating your study guide...';
        downloadBtn.style.display = 'none';
        
        // Collect form data
        const formData = {
            class: document.getElementById('className').value,
            unit: document.getElementById('unit').value,
            year: document.getElementById('year').value,
            details: document.getElementById('details').value
        };
        
        // Send form data to backend
        fetch('/generate-study-guide', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => {
            return response.json().then(data => {
                if (!response.ok) {
                    throw new Error(data.error || 'Network response was not ok');
                }
                return data;
            });
        })
        .then(data => {
            if (!data.success) {
                throw new Error(data.error || 'Failed to generate study guide');
            }
            
            // Hide loading, show content
            loadingElement.style.display = 'none';
            studyGuideContent.style.display = 'block';
            downloadBtn.style.display = 'block';
            
            // Display the generated study guide
            studyGuideContent.textContent = data.content;
            
            // Store the filename for download
            currentFilename = data.filename;
            
            // Add futuristic typing effect
            applyTypingEffect(studyGuideContent, data.content);
        })
        .catch(error => {
            console.error('Error generating study guide:', error);
            
            // Update loading message to show error
            loadingElement.querySelector('.spinner').style.borderTopColor = '#ff3366';
            loadingElement.querySelector('p').textContent = `Error: ${error.message || 'Unknown error occurred'}`;
            
            // Show error message after a delay
            setTimeout(() => {
                loadingElement.style.display = 'none';
                studyGuideContent.style.display = 'block';
                studyGuideContent.textContent = `Error generating study guide: ${error.message || 'Please try again later.'}`;
                
                // Add a retry button
                const retryButton = document.createElement('button');
                retryButton.textContent = 'Try Again';
                retryButton.className = 'btn-generate';
                retryButton.style.marginTop = '1rem';
                retryButton.onclick = () => {
                    resultContainer.style.display = 'none';
                    studyGuideContent.textContent = '';
                };
                studyGuideContent.parentNode.appendChild(retryButton);
            }, 2000);
        });
    });
    
    // Download button handler
    downloadBtn.addEventListener('click', function() {
        if (currentFilename) {
            window.location.href = `/download/${currentFilename}`;
            
            // Add visual feedback for the download
            const originalText = downloadBtn.textContent;
            downloadBtn.textContent = "Downloading...";
            downloadBtn.style.backgroundColor = "var(--primary-blue)";
            downloadBtn.style.color = "white";
            
            setTimeout(() => {
                downloadBtn.textContent = originalText;
                downloadBtn.style.backgroundColor = "";
                downloadBtn.style.color = "";
            }, 2000);
        }
    });
    
    // Futuristic typing effect function
    function applyTypingEffect(element, text) {
        const originalText = text;
        element.textContent = '';
        
        let i = 0;
        const typingSpeed = 1; // Adjust for faster/slower typing
        
        function typeNextChar() {
            if (i < originalText.length) {
                element.textContent += originalText.charAt(i);
                i++;
                setTimeout(typeNextChar, typingSpeed);
            }
        }
        
        // Start with existing content
        element.textContent = originalText;
        
        // Apply a highlight effect to simulate scanning
        element.classList.add('scanning');
        setTimeout(() => {
            element.classList.remove('scanning');
        }, 1000);
    }
    
    // Add some futuristic UI interactions
    const formInputs = document.querySelectorAll('input, select, textarea');
    
    formInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });
    
    // Add a visual indicator when AI is processing
    const addProcessingIndicator = () => {
        const loadingText = loadingElement.querySelector('p');
        let dots = 0;
        
        return setInterval(() => {
            dots = (dots + 1) % 4;
            const dotsText = '.'.repeat(dots);
            loadingText.textContent = `Generating your study guide${dotsText}`;
        }, 500);
    };
});