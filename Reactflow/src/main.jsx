import React, { useCallback } from "react";
import { createRoot } from "react-dom/client";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { toPng } from "html-to-image";

// 纯离线：无后端、无登录；节点/连线状态全在本地。
const initialNodes = [
  { id: "1", position: { x: 80, y: 80 }, data: { label: "开始" } },
  { id: "2", position: { x: 340, y: 200 }, data: { label: "处理" } },
];
const initialEdges = [{ id: "e1-2", source: "1", target: "2" }];

function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );
  const { screenToFlowPosition } = useReactFlow();

  const addNode = useCallback(() => {
    const id = String(nodes.length + 1);
    const pos = screenToFlowPosition
      ? screenToFlowPosition({ x: 200, y: 320 })
      : { x: 200, y: 320 };
    setNodes((nds) =>
      nds.concat({ id, position: pos, data: { label: "节点 " + id } })
    );
  }, [nodes.length, setNodes, screenToFlowPosition]);

  const exportPng = useCallback(() => {
    const el = document.querySelector(".react-flow");
    if (el) {
      toPng(el).then((dataUrl) => {
        const a = document.createElement("a");
        a.download = "flowchart.png";
        a.href = dataUrl;
        a.click();
      });
    }
  }, []);

  return (
    <div style={{ width: "100vw", height: "100vh" }}>
      <div
        style={{
          position: "absolute",
          zIndex: 10,
          top: 10,
          left: 10,
          display: "flex",
          gap: 8,
        }}
      >
        <button onClick={addNode}>添加节点</button>
        <button onClick={exportPng}>导出 PNG</button>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}

function App() {
  return (
    <ReactFlowProvider>
      <Flow />
    </ReactFlowProvider>
  );
}

createRoot(document.getElementById("root")).render(<App />);
