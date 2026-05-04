window.onload = () => {
  const ui = SwaggerUIBundle({
    url: window.ANTYPHISING_OPENAPI_URL,
    dom_id: '#swagger-ui',
    deepLinking: true,
    layout: 'BaseLayout',
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
    defaultModelsExpandDepth: -1,
    defaultModelExpandDepth: -1,
    docExpansion: 'list',
    displayRequestDuration: false,
    filter: true,
    tryItOutEnabled: true,
    persistAuthorization: true,
    displayOperationId: false,
    syntaxHighlight: { activated: true, theme: 'nord' },
  });

  const syncDom = () => {
    document.querySelectorAll('.opblock-tag').forEach(el => {
      const text = (el.textContent || '').trim().toLowerCase();
      if (text === 'health') el.style.borderLeft = '4px solid #5f8f80';
      if (text === 'incidents') el.style.borderLeft = '4px solid #6b86a7';
      if (text === 'ml') el.style.borderLeft = '4px solid #9b7bff';
    });
  };

  setTimeout(syncDom, 250);
  setTimeout(syncDom, 900);
  window.ui = ui;
};
