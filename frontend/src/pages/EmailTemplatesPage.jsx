import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp, Save, RotateCcw } from 'lucide-react';
import '../styles/EmailTemplatesPage.css';

export default function EmailTemplatesPage() {
  const [templates, setTemplates] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [editingType, setEditingType] = useState(null);
  const [supportedVars, setSupportedVars] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState({});
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  // Load templates and supported variables
  useEffect(() => {
    Promise.all([
      fetch('/api/email-templates').then(r => r.json()),
      fetch('/api/email-templates/variables/supported').then(r => r.json()),
    ])
      .then(([templatesData, varsData]) => {
        setTemplates(templatesData);
        setSupportedVars(varsData);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error loading templates:', err);
        setLoading(false);
      });
  }, []);

  const toggleExpand = (type) => {
    setExpanded(prev => ({
      ...prev,
      [type]: !prev[type]
    }));
  };

  const handleSubjectChange = (type, value) => {
    setTemplates(prev => prev.map(t =>
      t.template_type === type ? { ...t, subject: value } : t
    ));
  };

  const handleBodyChange = (type, value) => {
    setTemplates(prev => prev.map(t =>
      t.template_type === type ? { ...t, body: value } : t
    ));
  };

  const handleActiveToggle = (type) => {
    setTemplates(prev => prev.map(t =>
      t.template_type === type ? { ...t, is_active: !t.is_active } : t
    ));
  };

  const handleSave = async (type) => {
    const template = templates.find(t => t.template_type === type);
    setSaving(prev => ({ ...prev, [type]: true }));

    try {
      const response = await fetch(`/api/email-templates/${type}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: template.subject,
          body: template.body,
          is_active: template.is_active
        })
      });

      if (!response.ok) throw new Error('Failed to save template');

      setMessage(`Template "${type}" saved successfully`);
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      setMessage(`Error saving template: ${err.message}`);
    } finally {
      setSaving(prev => ({ ...prev, [type]: false }));
    }
  };

  const handleReset = async (type) => {
    // Reload from server
    try {
      const response = await fetch(`/api/email-templates/${type}`);
      if (!response.ok) throw new Error('Failed to load template');
      const updated = await response.json();

      setTemplates(prev => prev.map(t =>
        t.template_type === type ? updated : t
      ));

      setMessage(`Template "${type}" reset to saved version`);
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      setMessage(`Error loading template: ${err.message}`);
    }
  };

  if (loading) return <div className="loading">Loading templates...</div>;

  return (
    <div className="email-templates-page">
      <div className="page-header">
        <h1>Email Templates</h1>
        <p>Customize email content sent to clients. Use variables like {'{client_name}'} in templates.</p>
      </div>

      {message && <div className="message">{message}</div>}

      <div className="templates-container">
        {templates.map(template => (
          <div key={template.template_type} className="template-card">
            <div
              className="template-header"
              onClick={() => toggleExpand(template.template_type)}
              style={{ cursor: 'pointer' }}
            >
              <div className="header-left">
                {expanded[template.template_type] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                <div className="template-title">
                  <h3>{template.template_type.replace(/_/g, ' ')}</h3>
                  <p className="template-subject">{template.subject}</p>
                </div>
              </div>
              <div className="header-right">
                <label className="active-toggle">
                  <input
                    type="checkbox"
                    checked={template.is_active}
                    onChange={() => handleActiveToggle(template.template_type)}
                    onClick={e => e.stopPropagation()}
                  />
                  <span>Active</span>
                </label>
              </div>
            </div>

            {expanded[template.template_type] && (
              <div className="template-content">
                <div className="form-group">
                  <label>Subject</label>
                  <input
                    type="text"
                    value={template.subject}
                    onChange={(e) => handleSubjectChange(template.template_type, e.target.value)}
                    className="subject-input"
                  />
                </div>

                <div className="form-group">
                  <label>Body (HTML)</label>
                  <textarea
                    value={template.body}
                    onChange={(e) => handleBodyChange(template.template_type, e.target.value)}
                    className="body-textarea"
                    rows="15"
                  />
                </div>

                {supportedVars && (
                  <div className="variables-info">
                    <h4>Available Variables</h4>
                    <div className="variables-grid">
                      {supportedVars.variables.common.map(v => (
                        <code key={v} className="var-badge">{v}</code>
                      ))}
                    </div>
                    {supportedVars.variables.memo_specific.length > 0 && (
                      <>
                        <h5>Memo-Specific</h5>
                        <div className="variables-grid">
                          {supportedVars.variables.memo_specific.map(v => (
                            <code key={v} className="var-badge">{v}</code>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}

                <div className="template-actions">
                  <button
                    className="btn-save"
                    onClick={() => handleSave(template.template_type)}
                    disabled={saving[template.template_type]}
                  >
                    <Save size={16} />
                    {saving[template.template_type] ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    className="btn-reset"
                    onClick={() => handleReset(template.template_type)}
                    disabled={saving[template.template_type]}
                  >
                    <RotateCcw size={16} />
                    Reset
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
