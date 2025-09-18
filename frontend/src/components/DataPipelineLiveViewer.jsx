import React, { useEffect, useState } from 'react';
import './DataPipelineLiveViewer.css';

const endpoints = {
  kafkaIn: 'http://localhost:8081/kafka/in',
  agent: 'http://localhost:8081/agent',
  kafkaOut: 'http://localhost:8081/kafka/out',
};

const DataPipelineLiveViewer = () => {
  const [kafkaInData, setKafkaInData] = useState([]);
  const [agentLogs, setAgentLogs] = useState([]);
  const [kafkaOutData, setKafkaOutData] = useState([]);

  const fetchData = async () => {
    try {
      const [inRes, agentRes, outRes] = await Promise.all([
        fetch(endpoints.kafkaIn),
        fetch(endpoints.agent),
        fetch(endpoints.kafkaOut),
      ]);

      const inJson = await inRes.json();
      const agentJson = await agentRes.json();
      const outJson = await outRes.json();

      setKafkaInData(inJson.messages || []);
      setAgentLogs(agentJson.logs || []);
      setKafkaOutData(outJson.messages || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="viewer-container">
      <h1>Data Pipeline Live Viewer</h1>
      <div className="viewer-grid">
        <Section title="Kafka In" data={kafkaInData} />
        <Section title="Agent Logs" data={agentLogs} />
        <Section title="Kafka Out" data={kafkaOutData} />
      </div>
    </div>
  );
};

const Section = ({ title, data }) => (
  <div className="section">
    <h2>{title}</h2>
    <pre className="scrollable">
      {data.slice(-10).map((item, idx) => (
        <div key={idx}>{JSON.stringify(item, null, 2)}</div>
      ))}
    </pre>
  </div>
);

export default DataPipelineLiveViewer;
