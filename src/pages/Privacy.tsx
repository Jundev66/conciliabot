import LegalPage, { LegalSection } from "../components/LegalPage";

export default function Privacy() {
  return (
    <LegalPage title="Política de Privacidad" updated="octubre de 2026">
      <LegalSection title="1. Quién es el responsable">
        <p>
          En el modelo BYOC, el <strong>Cliente</strong> es el <strong>responsable del
          tratamiento</strong> de los datos que trata con el software, y{" "}
          <strong>[Razón social del proveedor]</strong> actúa como <strong>encargado</strong>,
          tratándolos solo según las instrucciones del Cliente y el contrato de tratamiento de datos
          (DPA). En esta <strong>demo</strong>, todos los datos son <strong>sintéticos</strong>.
        </p>
      </LegalSection>

      <LegalSection title="2. Qué datos se tratan">
        <ul className="list-disc space-y-1 pl-5">
          <li>Datos de facturas y comprobantes (proveedor, importes, impuestos, folios, UUID/CUFE).</li>
          <li>Datos de referencia del ERP (órdenes de compra, recepciones).</li>
          <li>Datos de uso y auditoría (quién aprobó, cuándo y qué).</li>
        </ul>
        <p>
          Los datos pueden incluir <strong>información personal</strong> de terceros (p. ej.,
          firmantes, contactos). Se aplica <strong>minimización</strong>: solo lo necesario.
        </p>
      </LegalSection>

      <LegalSection title="3. Para qué y con qué base legal">
        <p>
          La finalidad es <strong>conciliar, verificar y preparar el registro</strong> de facturas.
          La base legal se determina por el Cliente conforme a la normativa aplicable (por ejemplo,
          ejecución contractual o interés legítimo).
        </p>
      </LegalSection>

      <LegalSection title="4. Dónde viven los datos (BYOC)">
        <p>
          El software corre <strong>en el entorno del Cliente</strong>. Los Documentos y datos{" "}
          <strong>no se transfieren al Proveedor</strong>. Los modelos de IA se ejecutan de forma{" "}
          <strong>local o en la región elegida</strong> por el Cliente.
        </p>
      </LegalSection>

      <LegalSection title="5. Modelos de IA y subencargados">
        <p>
          La lista de subencargados (p. ej., proveedores de modelos o servicios) se detalla en el
          DPA. Si se usa un modelo externo, se exige <strong>retención cero</strong> y{" "}
          <strong>transferencia internacional válida</strong>; alternativamente se usan{" "}
          <strong>modelos locales</strong>.
        </p>
      </LegalSection>

      <LegalSection title="6. Conservación">
        <p>
          Los datos se conservan por el plazo que el Cliente defina según obligaciones fiscales
          aplicables (habitualmente entre <strong>5 y 10 años</strong>), tras lo cual se eliminan o
          se anonimizan.
        </p>
      </LegalSection>

      <LegalSection title="7. Seguridad">
        <ul className="list-disc space-y-1 pl-5">
          <li>Cifrado en tránsito y en reposo; claves gestionadas por el Cliente (KMS/BYOK).</li>
          <li>Aislamiento por entorno; mínimo privilegio en cada herramienta (sandbox).</li>
          <li>Redacción de PII y secretos antes de cualquier procesamiento con modelos.</li>
          <li>Bitácora de auditoría <strong>inmutable</strong> de cada acción y decisión.</li>
        </ul>
      </LegalSection>

      <LegalSection title="8. Decisiones automatizadas">
        <p>
          El software puede <strong>sugerir</strong> decisiones, pero toda acción con efecto fiscal
          o económico requiere <strong>revisión y aprobación humana</strong>. No se toman decisiones
          totalmente automatizadas con efectos jurídicos sobre las personas.
        </p>
      </LegalSection>

      <LegalSection title="9. Derechos de las personas">
        <p>
          Las personas pueden ejercer sus derechos (acceso, rectificación, supresión, oposición,
          etc.) ante el <strong>Cliente</strong> como responsable. El Proveedor asiste al Cliente
          para atender estas solicitudes conforme al DPA y la ley aplicable.
        </p>
      </LegalSection>

      <LegalSection title="10. Almacenamiento local (esta demo PWA)">
        <p>
          Esta demo guarda el estado en el <strong>almacenamiento local de tu navegador</strong>. No
          envía datos a ningún servidor. Puedes borrarlo con «Reiniciar demo» en Configuración o
          limpiando los datos del sitio.
        </p>
      </LegalSection>

      <LegalSection title="11. Contacto">
        <p>
          Privacidad y protección de datos: <strong>[correo de privacidad]</strong>.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
