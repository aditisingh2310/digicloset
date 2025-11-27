// Browser example: use fetch to POST an image
async function analyze(file){
  const form = new FormData();
  form.append('file', file);
  const res = await fetch('http://localhost:8000/analyze', { method: 'POST', body: form });
  const data = await res.json();
  console.log(data);
}
