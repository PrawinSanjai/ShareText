export function Tabs({ activeTab, items, onChange }) {
  return (
    <nav className="tabs" aria-label="Textie actions">
      {items.map((item) => (
        <button
          aria-selected={activeTab === item.id}
          className="tab-button"
          key={item.id}
          onClick={() => onChange(item.id)}
          type="button"
        >
          {item.Icon()}
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
