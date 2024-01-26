// Control modal forms

/**
 * Attaches a submit event listener to a form within a modal. 
 * This function handles the form submission via AJAX and updates a select element upon successful submission.
 *
 * @param {string} formId - The ID of the form to which the submit event listener will be attached.
 * @param {string} submitUrl - The URL to which the form data will be submitted via AJAX.
 * @param {string} selectElementId - The ID of the select element to be updated after successful form submission.
 * @param {string} modalId - The ID of the modal that contains the form.
 *
 * When the form (specified by formId) is submitted, this function prevents the default form submission
 * and instead sends the form data to the submitUrl via an AJAX POST request.
 * If the submission is successful, it dynamically updates the select element (specified by selectElementId)
 * with a new option based on the AJAX response, and then closes the modal (specified by modalId).
 * The function also handles any errors during the AJAX request and logs them to the console.
 */
function attachFormSubmitListener(formId, submitUrl, selectElementId, modalId) {
    $(formId).off('submit').on('submit', function(e) {
        e.preventDefault();
        e.stopPropagation();
        var formData = $(this).serialize();

        $.ajax({
            url: submitUrl,
            method: 'POST',
            data: formData,
            success: function(response) {
                var selectElement = document.getElementById(selectElementId);
                if (selectElement) {
                    var newOption = document.createElement("option");
                    var value, text;
                    
                    // A way to deal with multiple modal forms.

                    if (modalId.includes("Documento")){
                        value = response.documento_id;  
                        text = response.documento_name;
                    } else if(modalId.includes("Persona")) {
                        value = response.persona_id;
                        text = response.persona_name;
                    } else if(modalId.includes("Lugar")) {
                        value = response.lugar_id;
                        text = response.lugar_name;
                    } else if(modalId.includes("Archivo")) {
                        value = response.archivo_id;
                        text = response.archivo_name;
                    }
                    
                    newOption.value = value;
                    newOption.text = text;

                    selectElement.appendChild(newOption);
                    selectElement.value = value;
                }
                $(modalId).modal('hide');
            },
            error: function(xhr, status, error) {
                console.error("Error: ", status, error);
            }
        });
    });
}

/**
 * Binds an event to a button to load a form in a modal and handle its submission.
 *
 * @param {string} buttonId - The ID of the button that will trigger the modal when clicked.
 * @param {string} modalContentId - The ID of the HTML element where the modal content (form) will be loaded.
 * @param {string} formUrl - The URL from which the form content will be loaded into the modal.
 * @param {string} newFormId - The ID of the form that will be dynamically loaded into the modal.
 * @param {string} submitUrl - The URL to which the form data will be submitted.
 * @param {string} selectElementId - The ID of the select element that will be updated based on the form submission.
 * @param {string} modalId - The ID of the modal which contains the form.
 *
 * This function first checks if the environment is suitable for a secure connection and adjusts the submitUrl accordingly.
 * It then attaches a click event listener to the specified button. When the button is clicked, the form is loaded from
 * formUrl into the modal specified by modalContentId. It also attaches a form submission event listener to the loaded form.
 * On successful form submission, it updates the select element specified by selectElementId and closes the modal.
 */

function bindEventToButton(buttonId, modalContentId, formUrl, newFormId, submitUrl, selectElementId, modalId) {
    var button = document.getElementById(buttonId);
    var appHost = window.location;
    var subdomain = appHost.hostname.split(".")[0];
    var isIPAddress = /^\d/.test(subdomain);
    var protocolIsHttp = appHost.protocol === 'http:';
    if (protocolIsHttp || isIPAddress){
        var newSubmitUrl = submitUrl;
    } else if (subdomain != "www") {
        var submitUrlArray = submitUrl.split("/").slice(1);
        var newSubmitUrl = '/' + submitUrlArray.join('/');
    }
    console.log(newSubmitUrl);
    
    if (button) {
        button.addEventListener('click', function() {
            $(modalContentId).load(formUrl, function() {
                attachFormSubmitListener(newFormId, newSubmitUrl, selectElementId, modalId);
                $(modalId).modal('show');
            });
        });
    }
}

// clone formset fields

function cloneAndUpdateFormset(formsetContainerId, formClass, managementFormId) {
    var container = document.getElementById(formsetContainerId);
    var original = container.querySelector('.' + formClass);
    var clone = original.cloneNode(true);
    var totalForms = document.getElementById(managementFormId);

    // Clear the values in the cloned fields and update names
    var currentFormIndex = parseInt(totalForms.value);
    clone.querySelectorAll('input, select, textarea').forEach(function(input) {
        input.value = '';
        input.name = input.name.replace(/-\d+-/, '-' + currentFormIndex + '-');
        input.id = input.id.replace(/-\d+-/, '-' + currentFormIndex + '-');
    });

    // Append the cloned fields to the container
    container.appendChild(clone);

    // Increment the total forms count
    totalForms.value = currentFormIndex + 1;
}

function isFormFilled(form) {
    return Array.from(form.querySelectorAll('input, select, textarea')).some(input => {
        return input.value.trim() !== '';
    });
}

function removeAndUpdateFormset(formsetContainerId, formClass, managementFormId){
    var container = document.getElementById(formsetContainerId);
    var originals = container.querySelectorAll('.' + formClass);
    var totalForms = document.getElementById(managementFormId);

    var currentFormIndex = parseInt(totalForms.value);

    if (originals.length > 1) {
        var lastForm = originals[originals.length - 1];
        if (isFormFilled(lastForm)) {
            var confirmRemove = confirm("Are you sure you want to remove this form?");
            if (confirmRemove){
            lastForm.remove();
            totalForms.value = currentFormIndex - 1;
            }
        } else {
            lastForm.remove();
            totalForms.value = currentFormIndex - 1;
        }
    }
}