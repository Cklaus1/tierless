# UI design review

Review this React component (a data table with a "load more" button) for UI/UX and accessibility
problems. Enumerate every issue you find — visual, interaction, accessibility, states — and what
to change.

```jsx
function UserTable({ endpoint }) {
  const [rows, setRows] = useState([]);
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetch(`${endpoint}?page=${page}`).then(r => r.json()).then(d => setRows([...rows, ...d]));
  }, [page]);

  return (
    <div style={{ fontFamily: 'Arial', fontSize: 13 }}>
      <div style={{ display: 'flex' }}>
        <div style={{ width: 200, color: '#999' }}>Name</div>
        <div style={{ width: 200, color: '#999' }}>Email</div>
        <div style={{ width: 100, color: '#999' }}>Status</div>
      </div>
      {rows.map(u => (
        <div style={{ display: 'flex' }} onClick={() => openUser(u.id)}>
          <div style={{ width: 200 }}>{u.name}</div>
          <div style={{ width: 200 }}>{u.email}</div>
          <div style={{ width: 100, color: u.active ? 'green' : 'red' }}>
            {u.active ? 'Active' : 'Inactive'}
          </div>
        </div>
      ))}
      <div onClick={() => setPage(page + 1)}
           style={{ color: 'blue', cursor: 'pointer', marginTop: 10 }}>
        Load more
      </div>
    </div>
  );
}
```
