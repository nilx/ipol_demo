/*
	Copyright (c) 2005, 2006 Rafael Robayna

	Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

	Additional Contributions by: Morris Johns
*/

	/*
		todo:
		need to fix the error with drawing the function
		need to write tutorial for using CanvasWidget

		bugs: 
		needs to be positioned absolutly and referenced absolutly - this is an issue with how mouse events are interpreted in all browsers

		CanvasWidget is a base class that handles all event listening and triggering.  A person who wishes to write
		a widget for Canvas can easily extend CanvasWidget and the few simple methods deling with drawing the widget.

		Handles checking for the canvas element and the initalization of mouse event listeners.
		to use, the drawWidget and widgetActionPerformed functions need to be extended.
	*/


	var LineWidthWidget = CanvasWidget.extend({
		lineWidth: null,
		linePosition: null,
		
		constructor: function(canvasName, lineWidth, xpos, position) {
			this.lineWidth = lineWidth;
			this.linePosition = xpos;
			this.inherit(canvasName, position);
		},
		
		drawWidget: function() {
			this.context.clearRect(0,0,250,120);

			this.context.fillStyle = 'rgba(0,0,0,0.2)';
			this.context.fillRect(0, 0, 250, 76);

			this.context.strokeStyle = 'rgba(255,255,255,1)';
			this.context.moveTo(1, 38);
			this.context.lineTo(249, 38);
			this.context.stroke();

			this.context.strokeStyle = 'rgba(255,255,255,0.5)';
			this.context.moveTo(1, 19);
			this.context.lineTo(249, 19);
			this.context.moveTo(1, 57);
			this.context.lineTo(249, 57);
			this.context.stroke();
			
			this.context.beginPath();
// 			var linePosition = 2.4*Math.floor((this.lineWidth*255)/76);
			this.context.fillStyle = 'rgba(0,0,0,1)';
			//this.context.arc(linePosition, 38, this.lineWidth/2, 0, Math.PI*2, true);			
			this.context.arc( this.linePosition, 38, this.lineWidth/2, 0, Math.PI*2, true);
			this.context.fill();
			this.context.closePath();
		},
	
		checkWidgetEvent: function(e) {
			var mousePos = this.getCanvasMousePos(e);

			if(mousePos.x >= 0 && mousePos.x <= 255) {
				this.lineWidth = Math.floor(((mousePos.x)*76)/255) + 1;
				this.drawWidget();
				this.callWidgetListeners();
			}
		}
	});
