// Control modal forms

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