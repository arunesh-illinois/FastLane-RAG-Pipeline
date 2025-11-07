"use client";
import { count } from "console";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";

export default function Home() {
  // const wsRef = useRef<WebSocket | null>(null);
  const [medicationsList, setMedicationsList] = useState<
    Array<{ medicationId: string; quantity: number }>
  >([{ medicationId: "", quantity: 0 }]);
  const [medicationsState, setMedicationsState] = useState({});

  const [roomToMedicationsMap, setRoomToMedicationsMap] = useState({});
  let room_uuids = [
    "123e4567-e89b-12d3-a456-426614174000",
    "223e4567-e89b-12d3-a456-426614174000",
  ];
  /*
    {
  room_uuid: {
  meddications_list: {},
  count: }}
  */
  const [saveDisable, setSaveDisable] = useState(false);
  const [payload, setPayload] = useState({});
  const [medicationsMap, setMedicationsMap] = useState({});
  const [idToNameMap, setIdToNameMap] = useState({});

  const getMedications = async () => {
    try {
      const response = await fetch(
        "https://mocki.io/v1/af40dce2-a121-49c0-b981-5b2a91b1da28",
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Medications data:", data);
      //  = data.reduce((acc: any, medication: any) => {
      //   acc[medication.id] = medication.display_name;
      //   return acc;
      // }, {});
      // console.log("medications map:", medications);
      setMedicationsState(data);
      data.forEach((medication) => {
        setMedicationsMap((prev) => ({
          ...prev,
          [medication.id]: 0,
        }));
        setIdToNameMap((prev) => ({
          ...prev,
          [medication.id]: medication.display_name,
        }));
      });
      console.log("medications map:", medicationsMap);
    } catch (error) {
      console.error("Error fetching medications:", error);
    }
  };

  const sendOrder = async (room_uuid, medication_list) => {
    console.log("Preparing to send order... for list:", medication_list);
    setSaveDisable(true);
    let medication_list_filtered = medication_list.filter(
      (med) => med.medicationId !== "" && med.quantity > 0
    );

    if (medication_list_filtered.length === 0) {
      alert("No valid medications to send. Aborting order.");
      setSaveDisable(false);
      return;
    }
    const order = { room_uuid, medications: medication_list_filtered };

    // Update medicationsMap
    setMedicationsMap((prev) => {
      const updated = { ...prev };
      medication_list_filtered.forEach((med) => {
        updated[med.medicationId] =
          (updated[med.medicationId] || 0) + med.quantity;
      });
      return updated;
    });

    let copiedList = structuredClone(medication_list_filtered);
    // Compute new room object
    const prevRoom = roomToMedicationsMap[room_uuid] || {
      medications_list: [],
      total_orders: 0,
      medications_count: {},
    };

    const updatedMedicationsList = prevRoom.medications_list.concat(copiedList);

    console.log("updated medication: ", updatedMedicationsList);

    const updatedMedicationsCount = { ...prevRoom.medications_count };
    copiedList.forEach((med) => {
      updatedMedicationsCount[med.medicationId] =
        (updatedMedicationsCount[med.medicationId] || 0) + med.quantity;
    });

    const updatedRoom = {
      medications_list: updatedMedicationsList,
      total_orders: prevRoom.total_orders + 1,
      medications_count: updatedMedicationsCount,
    };

    setRoomToMedicationsMap((prev) => ({
      ...prev,
      [room_uuid]: updatedRoom,
    }));

    setPayload(order);

    setTimeout(() => {
      setSaveDisable(false);
    }, 2000);

    console.log("Order sent:", JSON.stringify(order));
    console.log("Updated room data:", updatedRoom);
  };

  const connect = () => {
    const ws = new WebSocket("wss://echo.websocket.events");
    // wsRef.current = ws;

    ws.onopen = () => {
      console.log("ws opened");
      ws.send("Hello WebSocket");
    };

    ws.onmessage = (event) => {
      console.log("event message: ", event.data);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("ws closed");
    };
  };

  useEffect(() => {
    getMedications();
    // connect();
    // const ws = new WebSocket("wss://echo.websocket.events");
    // // wsRef.current = ws;

    // ws.onopen = () => {
    //   console.log("ws opened");
    //   ws.send("Hello WebSocket");
    // };

    // ws.onmessage = (event) => {
    //   console.log("event message: ", event.data);
    // };

    // ws.onerror = (error) => {
    //   console.error("WebSocket error:", error);
    // };

    // ws.onclose = () => {
    //   console.log("ws closed");
    // };
  }, []);

  const addMedicationRow = () => {
    console.log("medicationsList:", medicationsList);
    setMedicationsList([
      ...medicationsList,
      { medicationId: medicationsState[0].id, quantity: 0 },
    ]);
    console.log("medicationsList:", medicationsList);
  };

  const removeMedication = (index: number) => {
    const list = [...medicationsList];
    list.splice(index, 1);
    setMedicationsList(list);
  };

  useEffect(() => {
    console.log("saveDisable changed:", saveDisable);
  }, [saveDisable]);

  useEffect(() => {
    console.log("medicationsList changed:", medicationsMap);
    Object.entries(medicationsMap).forEach(([id, count]) => {
      console.log("medication:", idToNameMap[id], "current count: ", count);
    });
  }, [medicationsMap]);

  const [selectedRoomId, setSelectedRoomId] = useState(room_uuids[0]);

  console.log("roomToMedicationsMap:", roomToMedicationsMap);
  return (
    <div className="bg-zinc-50 font-sans dark:bg-black flex flex-row justify-between items-center w-full">
      <main className="w-full flex flex-row justify-between items-start p-8 bg-white dark:bg-black mt-10">
        <div className="flex flex-col items-center gap-6 text-center sm:items-start sm:text-left">
          <select
            className="border p-2 rounded w-full mb-4"
            value={selectedRoomId}
            onChange={(e) => {
              setSelectedRoomId(e.target.value);
              setMedicationsList([
                { medicationId: medicationsState[0].id, quantity: 0 },
              ]);
            }}
          >
            {room_uuids.map((room_uuid) => (
              <option key={room_uuid} value={room_uuid}>
                Room {room_uuid}
              </option>
            ))}
          </select>
          {/* ROOM Order {selectedRoomId} */}
          {/* {medicationsList.map((medication, index) => ( */}
          <h3>ROOM Order {selectedRoomId}</h3>
          <div className="text-lg text-zinc-600 dark:text-zinc-400">
            {medicationsList.map((medication, index) => (
              <div key={index} className="mb-4">
                <select
                  className="border p-2 rounded w-full mb-2"
                  value={medication.medicationId}
                  onChange={(e) => {
                    const newList = [...medicationsList];
                    newList[index].medicationId = e.target.value;
                    setMedicationsList(newList);
                  }}
                >
                  <option value="">Select Medication</option>
                  {medicationsState &&
                    Object.entries(medicationsState).map(([key, med]: any) => (
                      <option key={med.id} value={med.id}>
                        {med.display_name}
                      </option>
                    ))}
                </select>
                <input
                  type="text"
                  placeholder="Quantity"
                  value={medication.quantity}
                  onChange={(e) => {
                    const newList = [...medicationsList];
                    newList[index].quantity = Number(e.target.value);
                    setMedicationsList(newList);
                  }}
                  className="border p-2 rounded w-full"
                />
                <button
                  className="mt-2 text-sm text-red-500"
                  onClick={() => removeMedication(index)}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={() => addMedicationRow()}
            className="rounded-full bg-black/10 px-10 py-3 font-semibold no-underline transition hover:bg-black/20 dark:bg-white/10 dark:hover:bg-white/20"
          >
            Add new medication
          </button>
          <button
            onClick={() => sendOrder(selectedRoomId, medicationsList)}
            disabled={saveDisable}
            className={`rounded-full px-10 py-3 font-semibold transition ${
              saveDisable
                ? "bg-gray-400 dark:bg-gray-700 cursor-not-allowed"
                : "bg-black/10 hover:bg-black/20 dark:bg-white/10 dark:hover:bg-white/20"
            }`}
          >
            {saveDisable ? "Sending..." : "Send Order"}
          </button>
        </div>
        <div className="mt-32 ml-30 flex flex-row items-center gap-2 sm:items-end">
          <pre className="break-words text-sm p-4 rounded">
            {JSON.stringify(roomToMedicationsMap, null, 2)}
          </pre>
        </div>
      </main>
    </div>
  );
}
