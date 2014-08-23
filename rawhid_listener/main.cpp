/****************************************************************************
* RawHID_Listener
* Small program that reads and writes to Teensy devices in RawHID mode.
* 
* Source:
* This code is modified from PJRC's demonstration code, available at:
*  http://pjrc.com/teensy/rawhid.html
* combined with an MSDN example for the Windows threading model.
*  http://msdn.microsoft.com/en-us/library/ms686927%28v=vs.85%29.aspx
*
* Originally, the prjc example compied under linux; but I couldn't come up
* with a way to interface with stdin effectively without using a threading model
* and couldn't find a good cross-platform threading model that mingw32-msvc could
* handle.
*
* Usage: Once the program opens, use the following commands:
    o to open the first device it finds
    n to open a device by name (see <i> for a list of names)
    c to close the device
    i to query connected devices
    
    > to send to the device
    p <id> <file> to pipe data stream <id> (0, 1, or 2) to file named <file>, 
         opened in append mode. Omitting <file> will close any open file handle.
    d <id> [on|off] to pipe data stream <id> (0, 1, or 2) to stdout in packet-dump form
          if 'on' is specified, and disable this feature if 'off' is specified.
    q to quit
*
* Normally, only the text stream is written to the console.
*
* TODO: This code really should be more secure -- I'm blatantly ignoring
* common wisdom about not using the secure versions of sscanf()...
*
* University of Washington / Ben Weiss / Summer 2014
* The MIT License (MIT)
* 
* Copyright (c) 2014 Ben Weiss
* 
* Permission is hereby granted, free of charge, to any person obtaining a copy
* of this software and associated documentation files (the "Software"), to deal
* in the Software without restriction, including without limitation the rights
* to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
* copies of the Software, and to permit persons to whom the Software is
* furnished to do so, subject to the following conditions:
* 
* The above copyright notice and this permission notice shall be included in
* all copies or substantial portions of the Software.
* 
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
* IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
* AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
* LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
* OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
* THE SOFTWARE.
*
*
******************************************************************************/

#include <windows.h>
#include <stdio.h>
#include <iostream>

#include "hid.h"

using namespace std;

// Constants ==========================================================
#define KEYBUF_SIZE    500      // needs to be < 516, the buffer defined internally in hid_WINDOWS.c
const unsigned int TX_TIMEOUT = 100;    // ms
const unsigned int TX_RETRIES = 3;      
const unsigned int RX_TIMEOUT = 100;    // ms

// Message flags. These are identical to the constants in rawhid_msg, except RX and TX are switched
#define TX_HEAD_DEVID           0x08      // this is backspace, and shouldn't appear in a normal text transmission...
#define RX_HEAD_DEVID           0xFC      // for querying the deviceid, this is the entire header (which is the same as an impossible 64-length text packet)

typedef enum {
  RX_PACK_TYPE_TEXT = 0x00,
  RX_PACK_TYPE_DATA0 = 0x01,
  RX_PACK_TYPE_DATA1 = 0x02,
  RX_PACK_TYPE_DATA2 = 0x03
} hid_pack_type;

#define RX_PACK_TYPE_MASK     0x03

// Local Variables ====================================================

int dev = -1;       // device handle
int quit = 0;       // flag to kill the threads.

// file handles for writing the different data streams out to files.
FILE *fdataout[3] = {NULL, NULL, NULL};
bool data_to_console[3] = {false, false, false};



HANDLE ghMutex;       // this mutex will govern the use of the usb library so we don't try to read and write simultaneously
// this may be overkill (the hid code implements its own mutex as well), but better safe than sorry.

// Local Functions ====================================================
DWORD WINAPI ConsoleWriter( LPVOID );
void dump_pack(const char *, int);
int do_receive();


DWORD WINAPI ConsoleReader( LPVOID );
int devopen(void);
int devopen_byname(int);
int devquery(void);
void process_line(const char *line, unsigned int len);


int main( void )
{
  HANDLE aThread[2];
  DWORD ThreadID;
  int i;

  printf("'RawHID Listener\n");
  fflush(stdout);


  // Create a mutex with no initial owner
  ghMutex = CreateMutex( 
    NULL,              // default security attributes
    FALSE,             // initially not owned
    NULL);             // unnamed mutex

  if (ghMutex == NULL) 
  {
    printf("'CreateMutex error: %d\n", GetLastError());
    fflush(stdout);
    return 1;
  }

  // Create 2 worker threads: One that reads from the device and writes to the console
  // and one that reads from the console and writes to the device.

  aThread[0] = CreateThread( 
    NULL,       // default security attributes
    0,          // default stack size
    (LPTHREAD_START_ROUTINE) ConsoleWriter, 
    NULL,       // no thread function arguments
    0,          // default creation flags
    &ThreadID); // receive thread identifier

  if( aThread[0] == NULL )
  {
    printf("'CreateThread error for Writer: %d\n", GetLastError());
    fflush(stdout);
    return 1;
  }
  aThread[1] = CreateThread( 
    NULL,       // default security attributes
    0,          // default stack size
    (LPTHREAD_START_ROUTINE) ConsoleReader, 
    NULL,       // no thread function arguments
    0,          // default creation flags
    &ThreadID); // receive thread identifier

  if( aThread[1] == NULL )
  {
    printf("'CreateThread error for Reader: %d\n", GetLastError());
    fflush(stdout);
    return 1;
  }

  // Wait for all threads to terminate

  WaitForMultipleObjects(2, aThread, TRUE, INFINITE);

  // Close thread and mutex handles

  for( i=0; i < 2; i++ )
    CloseHandle(aThread[i]);

  CloseHandle(ghMutex);

  return 0;
}


// This function is a thread. This thread will read packets from the device and write them to the console.
DWORD WINAPI ConsoleWriter( LPVOID lpParam )
{ 
  // lpParam not used in this example
  UNREFERENCED_PARAMETER(lpParam);

  DWORD dwWaitResult; 

  // Request ownership of mutex.

  while( !quit )
  { 
    dwWaitResult = WaitForSingleObject( 
      ghMutex,    // handle to mutex
      INFINITE);  // no time-out interval

    switch (dwWaitResult) 
    {
      // The thread got ownership of the mutex
    case WAIT_OBJECT_0: 
      
      if(dev >= 0)
        do_receive();
      fflush(stdout);

      // Release ownership of the mutex object
      if (! ReleaseMutex(ghMutex)) 
      { 
        // Handle error.
        printf("Failed to release mutex from Writer!\n");
        fflush(stdout);
      } 
      break; 

      // The thread got ownership of an abandoned mutex
      // The database is in an indeterminate state
    case WAIT_ABANDONED: 
      return FALSE; 
    }
  }
  return TRUE; 
}

// handles packets received from the device.
int do_receive()
{
  char buf[65];
  int num, datalen, i;
	// check if any Raw HID packet has arrived
	num = rawhid_recv(dev, buf, 64, RX_TIMEOUT);
	if (num < 0) {
		printf("\nerror reading, device went offline\n");
    fflush(stdout);
		rawhid_close(dev);
    dev = -1;
		return -1;
	}
	if (num > 0) {
		// validate this packet
    if (num < 64)
    {
      printf("Error reading. Got incomplete packet! Length = %i\n", num);
      fflush(stdout);
      dump_pack(buf, num);
      return -1;
    }
    else
    {
      // good packet. Write it to the console.
      // TODO: Implement escapes so we don't miss a 0 or 8 character that is
      // actually part of the stream.
      if((buf[0] & RX_PACK_TYPE_MASK) == RX_PACK_TYPE_TEXT)
      {
        // might not be a complete string.
        for(i = 0; i < 64; i++)
          if(0 == buf[i])
            break;
        if(64 == i)
          buf[64] = 0;
        printf("%s", buf + 1);
        fflush(stdout);
      }
      else
      {
        // binary packet; dump it to the console if that's enabled
        if(data_to_console[(buf[0] & RX_PACK_TYPE_MASK) - 1])   // we already dealt with buf[0] & 0b11 == 0 above in the text section.
          dump_pack(buf, num);
        // write it to the file, if available.
        datalen = buf[0] >> 2;    // read the actual packet length from the header.
        if(datalen < 64)
        {
          if(fdataout[(buf[0] & RX_PACK_TYPE_MASK) - 1])
            fwrite(buf + 1, 1, datalen, fdataout[(buf[0] & RX_PACK_TYPE_MASK) - 1]);
        }
        else
        {
          printf("Error: got invalid packet length from header: %i\n", datalen);
          fflush(stdout);
        }
      }
    }
  }
  return 0;
}

void dump_pack(const char *buf, int num)
{
  int i;
  printf("\nrecv %d bytes:\n", num);
  fflush(stdout);
  for (i=0; i<num; i++) {
    printf("%02X ", buf[i] & 255);
    if (i % 16 == 15 && i < num-1) printf("\n");
  }
  printf("\n");
  fflush(stdout);
}




// This function is a thread. This thread will read from the console (using cin, which blocks) and process lines when we have them.
DWORD WINAPI ConsoleReader( LPVOID lpParam )
{ 
  // lpParam not used in this example
  UNREFERENCED_PARAMETER(lpParam);
  char buf[100];

  DWORD dwWaitResult; 

  // Request ownership of mutex.

  while( !quit )
  { 

    cin.getline(buf, 100);   // block until we have a line of text

    dwWaitResult = WaitForSingleObject( 
      ghMutex,    // handle to mutex
      INFINITE);  // no time-out interval

    switch (dwWaitResult) 
    {
      // The thread got ownership of the mutex
    case WAIT_OBJECT_0: 

      // process the line we just read
      buf[99] = 0;
      process_line(buf, 100);
      
      // Release ownership of the mutex object
      if (! ReleaseMutex(ghMutex)) 
      { 
        printf("Failed to release mutex from Writer!\n");
        fflush(stdout);
      } 
      //} 
      break; 

      // The thread got ownership of an abandoned mutex
      // The database is in an indeterminate state
    case WAIT_ABANDONED: 
      return FALSE; 
    }
  }
  return TRUE; 
}

int devopen()
{
  int r;
	// C-based example is 16C0:0480:FFAB:0200
	r = rawhid_open(1, 0x16C0, 0x0480, 0xFFAB, 0x0200);
	if (r <= 0) {
		// Arduino-based example is 16C0:0486:FFAB:0200
		r = rawhid_open(1, 0x16C0, 0x0486, 0xFFAB, 0x0200);
		if (r <= 0) {
			printf("no rawhid device found\n");
      fflush(stdout);
			return -1;
		}
	}
	printf("found rawhid device 0\n");
  fflush(stdout);
  return 0;
}

// opens a device, given its name as shown in devquery
int devopen_byname(int name)
{
  int r, i;
  unsigned char out[64] = {TX_HEAD_DEVID, TX_HEAD_DEVID, TX_HEAD_DEVID};
  unsigned char in[64];
	// C-based example is 16C0:0480:FFAB:0200
	r = rawhid_open(10, 0x16C0, 0x0480, 0xFFAB, 0x0200);
	if (r <= 0) {
		// Arduino-based example is 16C0:0486:FFAB:0200
		r = rawhid_open(10, 0x16C0, 0x0486, 0xFFAB, 0x0200);
		if (r <= 0) {
			printf("no rawhid device found\n");
      fflush(stdout);
			return -1;
		}
	}
  dev = -1;
	for(i = 0; i < r; i++)
  {
    if(-1 == dev)
    {
      // send the packet query request:
      if(rawhid_send(i, out, 64, 100) >= 0)
      {
        // receive the response
        for(int k = 0; k < 100; k++)
        {
          if(rawhid_recv(i, in, 64, 100) >= 0)
          {
            if(RX_HEAD_DEVID == in[0])
            {
              if(name == in[1])
              {
                // We found a match!
                dev = i;
                printf("'Opened device %i\n", name);
                fflush(stdout);
              }
              break;
            }
          }
          else
            break;    // no sense re-trying the receive if it failed.
        }
      }
    }
    if(i != dev)
      rawhid_close(i);
  }
  if(-1 == dev)
    return -1;
  
  return 0;
}


// gathers the addresses of the different teensys plugged in by opening all of them and reading back their address packet.
int devquery()
{
  int r, i;
  unsigned char out[64] = {TX_HEAD_DEVID, TX_HEAD_DEVID, TX_HEAD_DEVID};
  unsigned char in[64];
	// C-based example is 16C0:0480:FFAB:0200
	r = rawhid_open(10, 0x16C0, 0x0480, 0xFFAB, 0x0200);
	if (r <= 0) {
		// Arduino-based example is 16C0:0486:FFAB:0200
		r = rawhid_open(10, 0x16C0, 0x0486, 0xFFAB, 0x0200);
		if (r <= 0) {
			printf("no rawhid device found\n");
      fflush(stdout);
			return -1;
		}
	}
	for(i = 0; i < r; i++)
  {
    // send the packet query request:
    if(rawhid_send(i, out, 64, 100) >= 0)
    {
      // receive the response
      for(int k = 0; k < 100; k++)
      {
        if(rawhid_recv(i, in, 64, 100) >= 0)
        {
          if(RX_HEAD_DEVID == in[0])
          {
            printf("%X\n", in[1]);
            break;
          }
        }
        else
          break;    // no sense re-trying the receive if it failed.
      }
    }
    rawhid_close(i);
  }
  printf("Found %i devices\n", r);
  fflush(stdout);
  
  return 0;
}


// handles a line of command input and processes it.
void process_line(const char *line, unsigned int len)
{
  int i;
  int a = 0, data_id = 0, n = 0;

  if(len < 1)
    return;
  // what kind of line is this?
  switch(line[0])
  {
  case '>': // line goes to device.
    if(dev >= 0)
    {
      for(i = 0; i < len / 64 + 1; i++)
      {
        if(rawhid_send(dev, (void*)(line + 1 + i*64), 64, TX_TIMEOUT) >= 0)
          break;
        printf("Send failed.\n");
        fflush(stdout);
      }
    }
    else
    {
      printf("Device not open!\n");
      fflush(stdout);
    }
    break;

  case 'o': // open a device.
    if(dev < 0)
      dev = devopen();
    else
    {
      printf("Device already open!\n");
      fflush(stdout);
    }
    break;

  case 'c': // close the device
    if(dev >= 0)
    {
      rawhid_close(dev);
      dev = -1;
      printf("Device closed.\n");
    }
    else
    {
      printf("Device not open!\n");
      fflush(stdout);
    }
    break;

  case 'i': // query devices attached.
    devquery();
    break;

  case 'n': // open device by name
    // the name is the first non-whitespace character
    if(sscanf(line + 1, " %i", &a) != 1)
    {
      printf("Could not read device name! '%s'\n", line + 1);
      fflush(stdout);
      break;
    }
    printf("Opening %i\n", a);
    fflush(stdout);
    if(0 == devopen_byname(a))
    {
      printf("Device open.\n");
      fflush(stdout);
    }
    else
    {
      printf("Could not open device.\n");
      fflush(stdout);
    }
    break;

  case 'p': // pipe a data stream to a file
    if(sscanf(line + 1, " %i%n", &data_id, &n) == 1)
    {
      n++;
      // we now have a device id. check it.
      if(0 <= data_id && 2 >= data_id)
      {
        // check -- is the file open? 
        if(fdataout[data_id])
          fclose(fdataout[data_id]);
        // try to read a filename
        if(*(line + n + 1) != '\0')
          fdataout[data_id] = fopen(line + n + 1, "ab");    // binary mode, append contents.
      }
      else
      {
        printf("Invalid data stream specified: %i\n", data_id);
        fflush(stdout);
      }
    }
    else
    {
      printf("Could not read device ID.\n");
      fflush(stdout);
    }
    break;

  case 'd':   // turn on/off dumping of data streams to console.
    if(sscanf(line + 1, " %i%n", &data_id, &n) == 1)
    {
      n++;
      // we now have a device id. check it.
      if(0 <= data_id && 2 >= data_id && n + 1 < len)
      {
        // try to read "on":
        sscanf(line + n + 1, " %n", &a);
        if(strncmp(line + n + a + 1, "on", 2) == 0)
        {
          data_to_console[data_id] = true;
          printf("Echoing data stream %i to console.\n", data_id);
          fflush(stdout);
        }
        else
        {
          data_to_console[data_id] = false;
          printf("Stopped echoing data stream %i to console.\n", data_id);
          fflush(stdout);
        }
      }
      else
      {
        printf("Invalid data stream specified: %i\n", data_id);
        fflush(stdout);
      }
    }
    else
    {
      printf("Could not read device ID.\n");
      fflush(stdout);
    }
    break;

  case 'q': // quit
    if(dev)
    {
      rawhid_close(dev);
      dev = -1;
    }
    quit = 1;   // signal shutdown time
    break;

  default :
    printf("I didn't understand what you meant. Please use the following commands:\n\
o to open the first device it finds\n\
n to open a device by name (see <i> for a list of names)\n\
c to close the device\n\
i to query connected devices\n\
\n\
> to send to the device\n\
p <id> <file> to pipe data stream <id> (0, 1, or 2) to file named <file>, \n\
     opened in append mode. Omitting <file> will close any open file handle.\n\
d <id> [on|off] to pipe data stream <id> (0, 1, or 2) to stdout in packet-dump form\n\
     if 'on' is specified, and disable this feature if 'off' is specified.\n\
q to quit\n");
    fflush(stdout);

  }
}


